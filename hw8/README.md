Пример запуска:
```bash
(hw8) bromigo@bromigo-dev:~/otus-python-professional/hw8$ time ./memc_load.py --pattern "data/*.tsv.gz"
[2022.01.22 19:42:58] I Memc loader started with options: {'test': False, 'log': None, 'dry': False, 'pattern': 'data/*.tsv.gz', 'idfa': '127.0.0.1:33013', 'gaid': '127.0.0.1:33014', 'adid': '127.0.0.1:33015', 'dvid': '127.0.0.1:33016'}
[2022.01.22 19:42:58] I Processing data/20170929000100.tsv.gz
[2022.01.22 19:45:27] I Acceptable error rate (0.0). Successfull load
[2022.01.22 19:45:27] I Processing data/20170929000200.tsv.gz
[2022.01.22 19:47:57] I Acceptable error rate (0.0). Successfull load
[2022.01.22 19:47:57] I Processing data/20170929000000.tsv.gz
[2022.01.22 19:50:26] I Acceptable error rate (0.0). Successfull load

real    7m28.851s
user    5m29.426s
sys     1m35.769s
```