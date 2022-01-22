#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import gzip
import sys
import time
import glob
import logging
import threading
from queue import Queue
from dataclasses import dataclass
from optparse import OptionParser
# brew install protobuf
# protoc  --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2
# pip install python-memcached
from pymemcache import Client
from pymemcache.exceptions import MemcacheUnexpectedCloseError


NORMAL_ERR_RATE = 0.01
RETRY_COUNT = 5
TIMEOUT_SECONDS = 10


@dataclass
class Event:
    pass


@dataclass
class ExitEvent(Event):
    pass


@dataclass
class InsertAppsInstalledEvent(Event):
    dev_type: str
    dev_id: str
    lat: int
    lon: int
    apps: list


@dataclass
class Stat:
    processed: int = 0
    errors: int = 0


class ConsumerThread(threading.Thread):
    def __init__(self, queue, stat: Stat, host, dry_run):
        threading.Thread.__init__(self)
        self.queue = queue
        self.host = host
        self.stat = stat
        if not dry_run:
            self.client = Client(host.split(':'))
        else:
            self.client = None

    def _insert_appsinstalled(self, appsinstalled: InsertAppsInstalledEvent):
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
        ua.apps.extend(appsinstalled.apps)
        packed = ua.SerializeToString()

        retry_count = 0
        start_time = time.time()
        if self.client is None:
            logging.debug("%s - %s -> %s" % (self.host, key, str(ua).replace("\n", " ")))
            return True

        while True:
            try:
                if self.client.set(key, packed):
                    return True
            except MemcacheUnexpectedCloseError:
                retry_count += 1
                if retry_count > RETRY_COUNT or time.time() - start_time > TIMEOUT_SECONDS:
                    logging.exception("Cannot write to memc %s: retries or timeout expired" % self.host)
                    return False

            except Exception as e:
                logging.exception("Cannot write to memc %s: %s" % (self.host, e))
                return False

    def run(self):
        while True:
            event = self.queue.get()
            if isinstance(event, ExitEvent):
                return

            ok = self._insert_appsinstalled(event)
            if ok:
                self.stat.processed += 1
            else:
                self.stat.errors += 1


class ProducerThread(threading.Thread):
    def __init__(self, options):
        threading.Thread.__init__(self)
        self.options = options

    def _parse_appsinstalled(self, line):
        line = line.decode('utf-8')
        line_parts = line.strip().split("\t")
        if len(line_parts) < 5:
            return
        dev_type, dev_id, lat, lon, raw_apps = line_parts
        if not dev_type or not dev_id:
            return
        try:
            apps = [int(a.strip()) for a in raw_apps.split(",")]
        except ValueError:
            apps = [int(a.strip()) for a in raw_apps.split(",") if a.isidigit()]
            logging.info("Not all user apps are digits: `%s`" % line)
        try:
            lat, lon = float(lat), float(lon)
        except ValueError:
            logging.info("Invalid geo coords: `%s`" % line)
        return InsertAppsInstalledEvent(
            dev_type=dev_type,
            dev_id=dev_id,
            lat=lat,
            lon=lon,
            apps=apps,
        )

    def _dot_rename(self, path):
        head, fn = os.path.split(path)
        # atomic in most cases
        os.rename(path, os.path.join(head, "." + fn))

    def _start_consumers(self, queues_map):
        consumers = []
        stats = []
        for t, q in queues_map.items():
            stat = Stat()
            stats.append(stat)
            c = ConsumerThread(
                queue=q,
                stat=stat,
                host=getattr(self.options, t),
                dry_run=self.options.dry,
            )
            c.start()
            consumers.append(c)

        return consumers, stats

    def _join_consumers(self, queues_map, consumers, stats):
        stat = Stat()

        for q in queues_map.values():
            q.put(ExitEvent())

        for c, s in zip(consumers, stats):
            c.join()
            stat.processed += s.processed
            stat.errors += s.errors

        return stat

    def run(self):
        queues_map = {}
        for t in ["idfa", "gaid", "adid", "dvid"]:
            queues_map[t] = Queue()

        for fn in glob.glob(self.options.pattern):
            errors = 0
            consumers, stats = self._start_consumers(queues_map)

            logging.info('Processing %s' % fn)
            fd = gzip.open(fn)
            for line in fd:
                line = line.strip()
                if not line:
                    continue
                appsinstalled = self._parse_appsinstalled(line)
                if not appsinstalled:
                    errors += 1
                    continue

                q = queues_map.get(appsinstalled.dev_type)
                if not q:
                    logging.error("Unknow device type: %s" % appsinstalled.dev_type)
                    return

                q.put(appsinstalled)

            stat: Stat = self._join_consumers(queues_map, consumers, stats)
            stat.errors += errors
            if not stat.processed:
                fd.close()
                self._dot_rename(fn)
                continue

            err_rate = float(stat.errors) / stat.processed
            if err_rate < NORMAL_ERR_RATE:
                logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
            else:
                logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))
            fd.close()
            self._dot_rename(fn)


def main(options):
    producer = ProducerThread(options)
    producer.start()
    producer.join()


def prototest():
    sample = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23\ngaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
    for line in sample.splitlines():
        dev_type, dev_id, lat, lon, raw_apps = line.strip().split("\t")
        apps = [int(a) for a in raw_apps.split(",") if a.isdigit()]
        lat, lon = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat
        ua.lon = lon
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == '__main__':
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option("--pattern", action="store", default="/data/appsinstalled/*.tsv.gz")
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    (opts, args) = op.parse_args()
    logging.basicConfig(filename=opts.log, level=logging.INFO if not opts.dry else logging.DEBUG,
                        format='[%(asctime)s] %(levelname).1s %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    if opts.test:
        prototest()
        sys.exit(0)

    logging.info("Memc loader started with options: %s" % opts)
    try:
        main(opts)
    except Exception as e:
        logging.exception("Unexpected error: %s" % e)
        sys.exit(1)
