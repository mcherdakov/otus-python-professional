# OTUServer

В качестве архтектуры использовался thread pool

Результат теста ApacheBench:
```(bash)
Server Software:        OTUServer
Server Hostname:        0.0.0.0
Server Port:            80

Document Path:          /httptest/dir2/
Document Length:        34 bytes

Concurrency Level:      100
Time taken for tests:   8.492 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      7700000 bytes
HTML transferred:       1700000 bytes
Requests per second:    5888.04 [#/sec] (mean)
Time per request:       16.984 [ms] (mean)
Time per request:       0.170 [ms] (mean, across all concurrent requests)
Transfer rate:          885.51 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.1      0       2
Processing:     2   17   2.6     17      42
Waiting:        1   17   2.6     17      39
Total:          3   17   2.6     17      42

Percentage of the requests served within a certain time (ms)
  50%     17
  66%     18
  75%     18
  80%     19
  90%     20
  95%     21
  98%     23
  99%     24
 100%     42 (longest request)
```