package main

import (
	"bufio"
	"compress/gzip"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"

	"github.com/bradfitz/gomemcache/memcache"
)

const NormalErrRate = 0.01

type AppsInstalled struct {
	devType string
	devID   string
	proto   *UserApps
}

type Loader struct {
	addrMap map[string]string
	dry     bool
	pattern string
}

type Stat struct {
	ok  int
	err int
}

func (loader *Loader) consumer(c chan *AppsInstalled, wg *sync.WaitGroup, name string, statIn chan *Stat) {
	addr := loader.addrMap[name]
	client := memcache.New(addr)
	stat := Stat{}

	log.Printf("starting consumer for %s with addr %s", name, addr)
	for appsInstalled := range c {
		key := fmt.Sprintf("%s:%s", appsInstalled.devType, appsInstalled.devID)
		if loader.dry {
			log.Printf(
				"%s - %s -> %s",
				addr, key, strings.Replace(appsInstalled.proto.String(), "\n", " ", -1),
			)
		} else {
			err := client.Set(&memcache.Item{
				Key:   key,
				Value: []byte(appsInstalled.proto.String()),
			})
			if err != nil {
				log.Printf("error sending %s: %v", key, err)
				stat.err += 1
				continue
			}
		}
		stat.ok += 1
	}

	log.Printf("consumer for %s finished", name)
	statIn <- &stat
	wg.Done()
}

func (loader *Loader) statCollector(recv chan *Stat, send chan *Stat) {
	totalStat := Stat{}

	for val := range recv {
		totalStat.ok += val.ok
		totalStat.err += val.err
	}

	send <- &totalStat
}

func (loader *Loader) parseLine(line string) (*AppsInstalled, error) {
	lineParts := strings.Split(line, "\t")
	if linePartsLen := len(lineParts); linePartsLen < 5 {
		return nil, fmt.Errorf("not enough line parts: %d < 5", linePartsLen)
	}
	devType, devID, rawLat, rawLon, rawApps := lineParts[0], lineParts[1], lineParts[2], lineParts[3], lineParts[4]
	if devType == "" || devID == "" {
		return nil, errors.New("dev type or dev id empty")
	}
	apps := []uint32{}
	faultyApps := []string{}
	for _, rawApp := range strings.Split(rawApps, ",") {
		app, err := strconv.Atoi(rawApp)
		if err != nil {
			faultyApps = append(faultyApps, rawApp)
		} else {
			apps = append(apps, uint32(app))
		}
	}
	if len(faultyApps) != 0 {
		log.Printf("not all user apps are digits: %v in line %s", faultyApps, line)
	}

	lat, latErr := strconv.ParseFloat(rawLat, 64)
	lon, lonErr := strconv.ParseFloat(rawLon, 64)
	if latErr != nil || lonErr != nil {
		log.Printf("invalid geo coords: %s", line)
	}

	return &AppsInstalled{
		devType: devType,
		devID:   devID,
		proto: &UserApps{
			Apps: apps,
			Lat:  &lat,
			Lon:  &lon,
		},
	}, nil
}

func (loader *Loader) processFile(path string, channelsMap map[string]chan *AppsInstalled, statIn chan *Stat) error {
	stat := Stat{}

	file, err := os.Open(path)
	if err != nil {
		return err
	}
	defer file.Close()

	reader, err := gzip.NewReader(file)
	if err != nil {
		return err
	}
	defer reader.Close()

	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		appsInstalled, err := loader.parseLine(line)
		if err != nil {
			log.Printf("Error while parsing line in %s: %v", path, err)
			stat.err += 1
			continue
		}
		channelsMap[appsInstalled.devType] <- appsInstalled
	}

	statIn <- &stat
	return nil
}

func (loader *Loader) closeChans(chans map[string]chan *AppsInstalled) {
	for _, c := range chans {
		close(c)
	}
}

func (loader *Loader) dotRename(path string) error {
	dir, file := filepath.Split(path)
	return os.Rename(path, filepath.Join(dir, "."+file))
}

func (loader *Loader) run() {
	channelsMap := make(map[string]chan *AppsInstalled, len(loader.addrMap))
	paths, err := filepath.Glob(loader.pattern)
	if err != nil {
		panic("failed to parse pattern")
	}

	for _, path := range paths {
		for name := range loader.addrMap {
			channelsMap[name] = make(chan *AppsInstalled)
		}
		wg := sync.WaitGroup{}
		statIn, statOut := make(chan *Stat), make(chan *Stat)
		go loader.statCollector(statIn, statOut)

		log.Printf("processing %s", path)

		for name, c := range channelsMap {
			wg.Add(1)
			go loader.consumer(c, &wg, name, statIn)
		}

		err := loader.processFile(path, channelsMap, statIn)
		loader.closeChans(channelsMap)
		wg.Wait()

		close(statIn)

		if err != nil {
			log.Printf("error occured while processing %s, skipping: %v", path, err)
			continue
		}

		stat := <-statOut

		if stat.ok == 0 {
			err := loader.dotRename(path)
			if err != nil {
				panic(err)
			}
			continue
		}

		errRate := float64(stat.err) / float64(stat.ok)
		if errRate < NormalErrRate {
			log.Printf("acceptable error rate (%f), successfull load", errRate)
		} else {
			log.Printf("high error rate (%f > %f), failed load", errRate, NormalErrRate)
		}

		err = loader.dotRename(path)
		if err != nil {
			panic(err)
		}
	}
}

func main() {
	var dry = flag.Bool("dry", false, "if true, don't actuall send anything to memcached")
	var pattern = flag.String("pattern", "/data/appsinstalled/*.tsv.gz", "path pattern with tsv files")
	var idfa = flag.String("idfa", "127.0.0.1:33013", "memcached address for idfa")
	var gaid = flag.String("gaid", "127.0.0.1:33014", "memcached address for gaid")
	var adid = flag.String("adid", "127.0.0.1:33015", "memcached address for adid")
	var dvid = flag.String("dvid", "127.0.0.1:33016", "memcached address for dvid")
	flag.Parse()

	addrMap := map[string]string{
		"idfa": *idfa,
		"gaid": *gaid,
		"adid": *adid,
		"dvid": *dvid,
	}

	log.Printf(
		"Memc loader started with options: dry=%t, pattern=%s, addrs: %v",
		*dry, *pattern, addrMap,
	)

	loader := &Loader{
		addrMap: addrMap,
		dry:     *dry,
		pattern: *pattern,
	}
	loader.run()
}
