## Pipeline comparison - mock
| condition       |   runs |   success_% |   wall_s_mean |   wall_s_sd |   llm_calls_mean |   llm_latency_ms_mean |   tokens_mean |   kernel_overhead_ms_mean |   kernel_overhead_ms_sd |   syscalls_mean |   quota_exceeded_mean |   deadlocks |
|:----------------|-------:|------------:|--------------:|------------:|-----------------:|----------------------:|--------------:|--------------------------:|------------------------:|----------------:|----------------------:|------------:|
| baseline        |     36 |         100 |          0.18 |        0.01 |                4 |                 40.43 |        311.5  |                      0    |                    0    |             nan |                   nan |           0 |
| agentos_relaxed |     36 |         100 |          0.27 |        0.02 |                4 |                 40.83 |        313.5  |                     46.02 |                    6.92 |              33 |                     0 |           0 |
| agentos_default |     36 |         100 |          0.22 |        0.02 |                3 |                 41.23 |        273.33 |                     46.62 |                   10.02 |              33 |                     1 |           0 |

Success % per seed:
| condition       |   0 |   1 |   2 |
|:----------------|----:|----:|----:|
| agentos_default | 100 | 100 | 100 |
| agentos_relaxed | 100 | 100 | 100 |
| baseline        | 100 | 100 | 100 |

Kernel overhead as % of wall time: mean 19.00%, max 32.52%

## Pipeline comparison - ollama_qwen2.5-1.5b
| condition       |   runs |   success_% |   wall_s_mean |   wall_s_sd |   llm_calls_mean |   llm_latency_ms_mean |   tokens_mean |   kernel_overhead_ms_mean |   kernel_overhead_ms_sd |   syscalls_mean |   quota_exceeded_mean |   deadlocks |
|:----------------|-------:|------------:|--------------:|------------:|-----------------:|----------------------:|--------------:|--------------------------:|------------------------:|----------------:|----------------------:|------------:|
| baseline        |     36 |       80.56 |         23.4  |        5.5  |                4 |               5845.18 |       1960.33 |                      0    |                    0    |          nan    |                   nan |           0 |
| agentos_relaxed |     36 |       80.56 |         21.66 |        4.88 |                4 |               5381.38 |       1866.61 |                     55.31 |                   12.58 |           32.97 |                     0 |           0 |
| agentos_default |     36 |       86.11 |         18.21 |        4.74 |                3 |               6027.48 |       1631.39 |                     53.07 |                   16.92 |           33    |                     1 |           0 |

Success % per seed:
| condition       |    0 |    1 |    2 |
|:----------------|-----:|-----:|-----:|
| agentos_default | 83.3 | 91.7 | 83.3 |
| agentos_relaxed | 75   | 91.7 | 75   |
| baseline        | 75   | 83.3 | 83.3 |

Kernel overhead as % of wall time: mean 0.29%, max 0.80%

## Mean dispatcher latency per syscall type (agentos_relaxed) - syscall_latency_mock.csv
| condition       | syscall          |   mean_latency_ms |   n_runs |
|:----------------|:-----------------|------------------:|---------:|
| agentos_relaxed | LLM_CALL         |            40.942 |       36 |
| agentos_relaxed | TOOL_CALL        |            14.885 |       36 |
| agentos_relaxed | FILE_WRITE       |             7.427 |       36 |
| agentos_relaxed | FILE_READ        |             0.25  |       36 |
| agentos_relaxed | SPAWN_AGENT      |             0.041 |       36 |
| agentos_relaxed | DEADLOCK_DETECT  |             0.026 |       36 |
| agentos_relaxed | BLACKBOARD_WRITE |             0.01  |       36 |
| agentos_relaxed | BLACKBOARD_READ  |             0.005 |       36 |
| agentos_relaxed | SET_QUOTA        |             0.004 |       36 |

## Mean dispatcher latency per syscall type (agentos_relaxed) - syscall_latency_ollama_qwen2.5-1.5b.csv
| condition       | syscall          |   mean_latency_ms |   n_runs |
|:----------------|:-----------------|------------------:|---------:|
| agentos_relaxed | LLM_CALL         |          5381.6   |       36 |
| agentos_relaxed | TOOL_CALL        |            16.998 |       36 |
| agentos_relaxed | FILE_WRITE       |             8.919 |       36 |
| agentos_relaxed | FILE_READ        |             0.369 |       36 |
| agentos_relaxed | DEADLOCK_DETECT  |             0.036 |       36 |
| agentos_relaxed | SPAWN_AGENT      |             0.018 |       36 |
| agentos_relaxed | BLACKBOARD_WRITE |             0.012 |       36 |
| agentos_relaxed | BLACKBOARD_READ  |             0.005 |       36 |
| agentos_relaxed | SET_QUOTA        |             0.004 |       36 |

## Deadlock / contention injection (capacity=6, claim K=3)
|                           |   trials |   stalled |   completed_% |   makespan_ms_mean |   makespan_ms_sd |   deadlocks_detected_mean |   restarts_mean |   refused_grants_mean |
|:--------------------------|---------:|----------:|--------------:|-------------------:|-----------------:|--------------------------:|----------------:|----------------------:|
| (4, 'bankers_off_detect') |       10 |         0 |         100   |              690.4 |            111.9 |                      10.6 |            10.6 |                 786.2 |
| (4, 'bankers_off_none')   |       10 |        10 |           0.5 |             2010   |              9.5 |                       0   |             0   |                3569.1 |
| (4, 'bankers_on')         |       10 |         0 |         100   |              489.8 |             37.3 |                       0   |             0   |                 467.4 |
| (6, 'bankers_off_detect') |       10 |         0 |         100   |             1822.9 |            297.5 |                      33.1 |            33.1 |                3661.2 |
| (6, 'bankers_off_none')   |       10 |        10 |           0   |             2006.5 |              2.6 |                       0   |             0   |                5296.1 |
| (6, 'bankers_on')         |       10 |         0 |         100   |              740.2 |             28.8 |                       0   |             0   |                1118.1 |
| (8, 'bankers_off_detect') |       10 |         0 |         100   |             4320.5 |           1020.7 |                      82.3 |            82.3 |               12359   |
| (8, 'bankers_off_none')   |       10 |        10 |           0   |             2007   |              2.1 |                       0   |             0   |                7038.4 |
| (8, 'bankers_on')         |       10 |         0 |         100   |             1017.6 |             46.4 |                       0   |             0   |                1971.8 |
