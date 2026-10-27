#ifndef STATS_H
#define STATS_H

#include <stddef.h>

typedef struct {
    size_t count;
    double min_us;
    double max_us;
    double median_us;
    double mean_us;
    double std_us;
    double p90_us;
    double p95_us;
    double p99_us;
    double iqr_us;
    double mad_us;
} OpStats;

OpStats compute_stats(double *samples, size_t n);

#endif // STATS_H
