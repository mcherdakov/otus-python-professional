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
MEMC_CLIENT_CONNECT_TIMEOUT_SECONDS = 20
MEMC_BUFFER_SIZE = 10


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
        super().__init__()
        self.queue = queue
        self.host = host
        self.stat = stat
        if not dry_run:
            self.client = Client(host.split(':'), timeout=MEMC_CLIENT_CONNECT_TIMEOUT_SECONDS)
        else:
            self.client = None

    def _insert_multi(self, values: dict[str, appsinstalled_pb2.UserApps]):
        if self.client is None:
            for key, ua in values.items():
                logging.debug("%s - %s -> %s" % (self.host, key, str(ua).replace("\n", " ")))
            self.stat.processed += len(values)
            return True

        unprocessed_values = {k: ua.SerializeToString() for k, ua in values.items()}
        retry_count = 0
        start_time = time.time()
        while True:
            try:
                faulty = set(self.client.set_multi(unprocessed_values))
                unprocessed_values = {k: v for k, v in unprocessed_values.items() if k in faulty}
                if len(unprocessed_values) == 0:
                    break
                else:
                    retry_count += 1
                    logging.exception("Failed to write some_values to memc: %s, retrying...", faulty)
            except MemcacheUnexpectedCloseError:
                retry_count += 1
            except Exception as e:
                logging.exception("Cannot write to memc %s: %s" % (self.host, e))
                break

            if retry_count > RETRY_COUNT or time.time() - start_time > TIMEOUT_SECONDS:
                logging.exception("Cannot write to memc %s: retries or timeout expired" % self.host)
                break

        self.stat.errors += len(unprocessed_values)
        self.stat.processed += len(values) - len(unprocessed_values)

    def _get_appsinstalled(self, appsinstalled: InsertAppsInstalledEvent) -> tuple[str, appsinstalled_pb2.UserApps]:
        ua = appsinstalled_pb2.UserApps()
        ua.lat = appsinstalled.lat
        ua.lon = appsinstalled.lon
        key = "%s:%s" % (appsinstalled.dev_type, appsinstalled.dev_id)
        ua.apps.extend(appsinstalled.apps)
        return key, ua

    def run(self):
        buffer: dict[str, appsinstalled_pb2.UserApps] = dict()
        while True:
            event = self.queue.get()
            if isinstance(event, ExitEvent):
                self._insert_multi(buffer)
                return

            key, val = self._get_appsinstalled(event)
            buffer[key] = val

            if len(buffer) > MEMC_BUFFER_SIZE:
                self._insert_multi(buffer)
                buffer = dict()


class FileProcessor:
    def __init__(self, path, queues_map):
        self.path = path
        self.queues_map = queues_map
        self.errors = 0

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

    def _dot_rename(self):
        head, fn = os.path.split(self.path)
        # atomic in most cases
        os.rename(self.path, os.path.join(head, "." + fn))

    def parse(self):
        logging.info('Processing %s' % self.path)

        with gzip.open(self.path) as fd:
            for line in fd:
                line = line.strip()
                if not line:
                    continue
                appsinstalled = self._parse_appsinstalled(line)
                if not appsinstalled:
                    self.errors += 1
                    continue

                q = self.queues_map.get(appsinstalled.dev_type)
                if not q:
                    logging.error("Unknow device type: %s" % appsinstalled.dev_type)
                    return

                q.put(appsinstalled)

    def collect_stat(self, stat: Stat):
        stat.errors += self.errors
        if not stat.processed:
            self._dot_rename()
            return

        err_rate = float(stat.errors) / stat.processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info("Acceptable error rate (%s). Successfull load" % err_rate)
        else:
            logging.error("High error rate (%s > %s). Failed load" % (err_rate, NORMAL_ERR_RATE))

        self._dot_rename()


class ProducerThread(threading.Thread):
    def __init__(self, options):
        super().__init__()
        self.options = options

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

    def _join_consumers(self, queues_map, consumers, stats) -> Stat:
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
            consumers, stats = self._start_consumers(queues_map)
            fp = FileProcessor(fn, queues_map)
            fp.parse()

            stat = self._join_consumers(queues_map, consumers, stats)
            fp.collect_stat(stat)


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
