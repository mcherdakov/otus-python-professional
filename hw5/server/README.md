# OTUServer

В качестве архтектуры использовался thread pool

Результат теста ApacheBench:
```(bash)
Server Software:        OTUServer
Server Hostname:        0.0.0.0
Server Port:            80

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   5.754 seconds
Complete requests:      50000
Failed requests:        0
Non-2xx responses:      50000
Total transferred:      4100000 bytes
HTML transferred:       0 bytes
Requests per second:    8690.03 [#/sec] (mean)
Time per request:       11.507 [ms] (mean)
Time per request:       0.115 [ms] (mean, across all concurrent requests)
Transfer rate:          695.88 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.1      0       2
Processing:     1   11   1.3     11      23
Waiting:        1   11   1.2     11      22
Total:          2   11   1.3     11      23

Percentage of the requests served within a certain time (ms)
  50%     11
  66%     12
  75%     12
  80%     12
  90%     13
  95%     13
  98%     15
  99%     16
 100%     23 (longest request)
```