# Python vanilla server

## Описание

- Сервер реализован по асинхронной техологии.
- Сервер работает с GET и HEAD запросами.

- Серверу можно указать DOCUMENT_ROOT через ```-r "./dir"```
- Серверу можно указать кол-во workers через ```-w 1```

## Результат нагрузочного тестирования

```ab -n 50000 -c 100 -r http://localhost:8080/httptest/wikipedia_russia.html```

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

Document Path:          /httptest/wikipedia_russia.html
Document Length:        954824 bytes

Concurrency Level:      100
Time taken for tests:   102.798 seconds
Complete requests:      50000
Failed requests:        0
Total transferred:      47748640440 bytes
HTML transferred:       47741200000 bytes
Requests per second:    486.39 [#/sec] (mean)
Time per request:       205.596 [ms] (mean)
Time per request:       2.056 [ms] (mean, across all concurrent requests)
Transfer rate:          453604.00 [Kbytes/sec] received

Connection Times (ms)
              min  mean[+/-sd] median   max
Connect:        0    0   6.5      0    1021
Processing:     2  205 187.2    231     497
Waiting:        1  198 188.5    163     492
Total:          2  205 187.4    234    1420

Percentage of the requests served within a certain time (ms)
  50%    234
  66%    382
  75%    391
  80%    396
  90%    409
  95%    420
  98%    440
  99%    455
 100%   1420 (longest request)
```
