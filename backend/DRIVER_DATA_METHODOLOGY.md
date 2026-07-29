# Driver Data Methodology

**Caveat**: *These are illustrative estimates derived from teammate-relative race pace, not official or definitive skill ratings. Car performance dominates raw lap time and cannot be fully separated from driver skill using public timing data alone.*

## The Teammate-Delta Method

Raw lap times in Formula 1 are overwhelmingly dictated by the performance of the car. Comparing a Red Bull driver's raw lap times to a Williams driver's lap times yields no useful information about the relative skill of the drivers.

To isolate the "driver effect," this simulator uses the **teammate-delta comparison** method:
1. **Data Source**: FastF1 telemetry from the 2023 season. We exclude qualifying and focus strictly on race pace.
2. **Detrending**: Raw lap times are detrended to remove the effects of tire degradation and fuel burn. We subtract the expected tire degradation (using our simulation model) and the expected fuel weight penalty from each lap. This yields "clean" pace times.
3. **Delta Computation**: For each race, we compare the detrended lap times of a driver against their teammate when running on comparable stints (same compound, similar tire age window).
4. **Pace Offset**: We average these deltas across the season to compute a `pace_offset`. A value of `-0.15` means the driver is, on average, 0.15s faster per lap than their teammate baseline. (Note: Since this is zero-sum within a team, the scale isn't absolute across different cars/teams).
5. **Consistency**: We compute the standard deviation of each driver's detrended lap times. This forms the `consistency` parameter. A lower standard deviation indicates higher consistency. Consistency is statistically more reliable than pace offset because variance is less confounded by the car's overall speed limit.

### Excluded Parameters

We explicitly **do not** compute or simulate a separate `tire_management` parameter in v4. Early pitters often look "tire-gentle" without actually being so, and it is impossible to separate tire management skill from strategy choice without controlling for stint length. This level of granularity is out of scope for the current model.
