#include <stdlib.h>
#include <string.h>
#include <math.h>

#include "stats.h"

static int compare_doubles(const void *a, const void *b) {
    double arg1 = *(const double *)a;
    double arg2 = *(const double *)b;
    if (arg1 < arg2) return -1;
    if (arg1 > arg2) return 1;
    return 0;
}

OpStats compute_stats(double *samples, size_t n) {
    OpStats st;
    memset(&st, 0, sizeof(st));
    if (n == 0) return st;
    st.count = n;

    double *sorted = malloc(n * sizeof(double));
    memcpy(sorted, samples, n * sizeof(double));
    qsort(sorted, n, sizeof(double), compare_doubles);

    st.min_us = sorted[0];
    st.max_us = sorted[n - 1];

    if (n % 2 == 1) {
        st.median_us = sorted[n / 2];
    } else {
        st.median_us = (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0;
    }

    size_t idx90 = (size_t)ceil(0.90 * n) - 1;
    size_t idx95 = (size_t)ceil(0.95 * n) - 1;
    size_t idx99 = (size_t)ceil(0.99 * n) - 1;
    size_t idx25 = (size_t)ceil(0.25 * n) - 1;
    size_t idx75 = (size_t)ceil(0.75 * n) - 1;

    st.p90_us = sorted[idx90 < n ? idx90 : n - 1];
    st.p95_us = sorted[idx95 < n ? idx95 : n - 1];
    st.p99_us = sorted[idx99 < n ? idx99 : n - 1];
    st.iqr_us = sorted[idx75 < n ? idx75 : n - 1] - sorted[idx25 < n ? idx25 : 0];

    double sum = 0.0;
    for (size_t i = 0; i < n; i++) {
        sum += samples[i];
    }
    st.mean_us = sum / (double)n;

    double var_sum = 0.0;
    for (size_t i = 0; i < n; i++) {
        double diff = samples[i] - st.mean_us;
        var_sum += diff * diff;
    }
    st.std_us = (n > 1) ? sqrt(var_sum / (double)(n - 1)) : 0.0;

    double *devs = malloc(n * sizeof(double));
    for (size_t i = 0; i < n; i++) {
        devs[i] = fabs(sorted[i] - st.median_us);
    }
    qsort(devs, n, sizeof(double), compare_doubles);
    if (n % 2 == 1) {
        st.mad_us = devs[n / 2];
    } else {
        st.mad_us = (devs[n / 2 - 1] + devs[n / 2]) / 2.0;
    }

    free(sorted);
    free(devs);
    return st;
}
