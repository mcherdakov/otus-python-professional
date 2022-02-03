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
	"time"

	"github.com/bradfitz/gomemcache/memcache"
)

const NormalErrRate = 0.01
const NLoaders = 3
const MemcTimeout = time.Second * 10

type AppsInstalled struct {
	devType string
	devID   string
	proto   *UserApps
}

type Stat struct {
	ok  int
	err int
}

func statCollector(recv chan *Stat, send chan *Stat) {
	totalStat := Stat{}

	for val := range recv {
		totalStat.ok += val.ok
		totalStat.err += val.err
	}

	send <- &totalStat
}

type MemcLoader struct {
	addrMap map[string]string
	dry     bool
	cIn     chan *AppsInstalled
	wg      *sync.WaitGroup
	name    string
	statIn  chan *Stat
}

func (ml *MemcLoader) run() {
	addr := ml.addrMap[ml.name]
	client := memcache.New(addr)
	client.Timeout = MemcTimeout
	stat := Stat{}

	log.Printf("starting consumer for %s with addr %s", ml.name, addr)
	for appsInstalled := range ml.cIn {
		key := fmt.Sprintf("%s:%s", appsInstalled.devType, appsInstalled.devID)
		if ml.dry {
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

	log.Printf("consumer for %s finished", ml.name)
	ml.statIn <- &stat
	ml.wg.Done()
}

type FileProcessor struct {
	path        string
	channelsMap map[string][]chan *AppsInstalled
	statIn      chan *Stat
}

func (fp *FileProcessor) parseLine(line string) (*AppsInstalled, error) {
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

func (fp *FileProcessor) process() error {
	stat := Stat{}

	file, err := os.Open(fp.path)
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

	chanNo := map[string]int{}
	for name := range fp.channelsMap {
		chanNo[name] = 0
	}

	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" {
			continue
		}
		appsInstalled, err := fp.parseLine(line)
		if err != nil {
			log.Printf("Error while parsing line in %s: %v", fp.path, err)
			stat.err += 1
			continue
		}
		dType := appsInstalled.devType
		fp.channelsMap[dType][chanNo[dType]] <- appsInstalled
		chanNo[dType] = (chanNo[dType] + 1) % NLoaders
	}

	fp.statIn <- &stat
	return nil
}

func (fp *FileProcessor) dotRename() error {
	dir, file := filepath.Split(fp.path)
	return os.Rename(fp.path, filepath.Join(dir, "."+file))
}

func (ctrl *Controller) closeChans(chansMap map[string][]chan *AppsInstalled) {
	for _, chans := range chansMap {
		for _, c := range chans {
			close(c)
		}
	}
}

type Controller struct {
	addrMap map[string]string
	dry     bool
	pattern string
}

func (ctrl *Controller) run() {
	channelsMap := make(map[string][]chan *AppsInstalled, len(ctrl.addrMap))
	paths, err := filepath.Glob(ctrl.pattern)
	if err != nil {
		panic("failed to parse pattern")
	}

	for _, path := range paths {
		for name := range ctrl.addrMap {
			chans := make([]chan *AppsInstalled, NLoaders)
			for i := range chans {
				chans[i] = make(chan *AppsInstalled)
			}
			channelsMap[name] = chans
		}
		wg := sync.WaitGroup{}
		statIn, statOut := make(chan *Stat), make(chan *Stat)
		go statCollector(statIn, statOut)

		log.Printf("processing %s", path)

		for name, chans := range channelsMap {
			for _, c := range chans {
				wg.Add(1)
				memcLoader := MemcLoader{
					addrMap: ctrl.addrMap,
					dry:     ctrl.dry,
					cIn:     c,
					wg:      &wg,
					name:    name,
					statIn:  statIn,
				}
				go memcLoader.run()
			}
		}

		fileProcessor := FileProcessor{
			path:        path,
			channelsMap: channelsMap,
			statIn:      statIn,
		}

		err := fileProcessor.process()

		ctrl.closeChans(channelsMap)
		wg.Wait()
		close(statIn)

		if err != nil {
			log.Printf("error occured while processing %s, skipping: %v", path, err)
			continue
		}

		stat := <-statOut

		if stat.ok == 0 {
			err := fileProcessor.dotRename()
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

		err = fileProcessor.dotRename()
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

	ctrl := &Controller{
		addrMap: addrMap,
		dry:     *dry,
		pattern: *pattern,
	}
	ctrl.run()
}
