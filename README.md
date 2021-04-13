# Python vanilla server

## Описание

Сервер реализован по асинхронной техологии.
Сервер работает с GET и HEAD запросами.

Серверу можно указать DOCUMENT_ROOT через ```-r "./dir"```
Серверу можно указать кол-во workers через ```-w 1```

## Результат нагрузочного тестирования

```ab -n 50000 -c 100 -r http://localhost:8080/```

```
This is ApacheBench, Version 2.3 <$Revision: 1843412 $>
Copyright 1996 Adam Twiss, Zeus Technology Ltd, http://www.zeustech.net/
Licensed to The Apache Software Foundation, http://www.apache.org/

Benchmarking localhost (be patient)
Completed 5000 requests
Completed 10000 requests
Completed 15000 requests
Completed 20000 requests
Completed 25000 requests
Completed 30000 requests
Completed 35000 requests
Completed 40000 requests
Completed 45000 requests
Completed 50000 requests
Finished 50000 requests


Server Software:        plhome/1.0
Server Hostname:        localhost
Server Port:            8080

Document Path:          /
Document Length:        0 bytes

Concurrency Level:      100
Time taken for tests:   6497.737 seconds
Complete requests:      50000
Failed requests:        0
Non-2xx responses:      50000
Total transferred:      5085875 bytes
HTML transferred:       0 bytes
Requests per second:    7.69 [#/sec] (mean)
Time per request:       12995.473 [ms] (mean)
Time per request:       129.955 [ms] (mean, across all concurrent requests)
Transfer rate:          0.76 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   0.4      0      15
Processing:   500 12947 15025.5   5491   49672
Waiting:      500 12947 15025.6   5490   49672
Total:        500 12947 15025.5   5491   49672

Percentage of the requests served within a certain time (ms)
  50%   5491
  66%   7906
  75%  26646
  80%  34820
  90%  39624
  95%  41187
  98%  43222
  99%  44732
 100%  49672 (longest request)
```
