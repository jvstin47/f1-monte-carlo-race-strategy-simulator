/**
 * Application Constants and Default Configurations.
 */

export const DEFAULT_STRATEGY_A = {
  driver_id: 'generic',
  track_id: 'bahrain',
  compound_1: 'soft',
  compound_2: 'medium',
  pit_lap: 18,
  compounds: ['soft', 'medium'],
  pit_laps: [18],
  num_laps: 57,
  base_lap_time: 94.0,
  pit_stop_time_loss: 22.0,
  num_simulations: 10000,
  random_std: 0.15,
  sc_probability: 0.04,
  is_reactive_sc: false,
  reactive_window: 8,
};

export const DEFAULT_STRATEGY_B = {
  driver_id: 'generic',
  track_id: 'bahrain',
  compound_1: 'medium',
  compound_2: 'hard',
  pit_lap: 30,
  compounds: ['medium', 'hard'],
  pit_laps: [30],
  num_laps: 57,
  base_lap_time: 94.0,
  pit_stop_time_loss: 22.0,
  num_simulations: 10000,
  random_std: 0.15,
  sc_probability: 0.04,
  is_reactive_sc: true,
  reactive_window: 8,
};

export const DEFAULT_UNDERCUT_INPUT = {
  base_pit_lap_b: 22,
  car_a_compound_1: 'medium',
  car_a_compound_2: 'hard',
  car_b_compound_1: 'medium',
  car_b_compound_2: 'hard',
  initial_gap_seconds: 1.0,
  dirty_air_penalty: 0.25,
  num_simulations: 5000,
};

export const VIEW_TABS = [
  { id: 'sim', label: 'Race Sim', icon: 'Play' },
  { id: 'sc', label: 'Safety Car Analysis', icon: 'ShieldAlert' },
  { id: 'weather', label: 'Weather Variance', icon: 'BarChart2' },
  { id: 'undercut', label: 'Undercut Engine', icon: 'Zap' },
  { id: 'optimize', label: 'DP Optimizer', icon: 'Sliders' },
  { id: 'fastf1', label: 'FastF1 Validation', icon: 'Database' },
];
