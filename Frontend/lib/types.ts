export type Status = "ok" | "warning" | "critical" | "unknown";
export type Urgency = "nominal" | "elevated" | "critical";

export interface BatteryAnalytics {
  health_pct: number;
  remaining_months: number;
  urgency: Urgency;
  primary_driver: string;
  prescriptive_action: string;
}

export interface Component {
  name: string;
  status: Status;
  metric_value: string;
  reason: string;
}

export interface Vehicle {
  vehicle_id: string;
  brand: string;
  model: string;
  odometer_km: number;
  climate_zone: string;
  overall_health_score: number;
  overall_status: Exclude<Status, "unknown">;
  projected_cost_at_risk_usd: number;
  battery_analytics: BatteryAnalytics;
  components: Component[];
  unmapped_signals: string[];
  missing_signals: string[];
  /** null (or absent) when no AI note was generated for this car */
  ai_explanation?: string | null;
}

export type DataSource = "live" | "fallback";

export interface FleetResult {
  vehicles: Vehicle[];
  source: DataSource;
  /** Why the fallback was used, when source === "fallback" */
  reason?: string;
  summary?: string | null;
}
