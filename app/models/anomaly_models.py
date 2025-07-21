from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

# --- Bottom-up model definitions ---

# 1. A generic model for statistical descriptions (min, max, mean, etc.)
class StatsModel(BaseModel):
    min: Optional[float] = None
    max: Optional[float] = None
    mean: Optional[float] = None
    std: Optional[float] = None
    p25: Optional[float] = Field(None, alias="25%")
    p50: Optional[float] = Field(None, alias="50%") # median
    p75: Optional[float] = Field(None, alias="75%")
    count: Optional[int] = None

    class Config:
        from_attributes = True
        populate_by_name = True

# 2. A model for a set of features, where each feature has its own stats
class DataSetStatsModel(BaseModel):
    total_appearances: Optional[StatsModel] = None
    total_time_seen_hours: Optional[StatsModel] = None
    distinct_sites_visited: Optional[StatsModel] = None
    distinct_zones_visited: Optional[StatsModel] = None
    critical_zone_visits: Optional[StatsModel] = None
    restricted_zone_visits: Optional[StatsModel] = None
    is_single_sighting: Optional[StatsModel] = None
    is_weekend_day: Optional[StatsModel] = None
    num_after_hours_events: Optional[StatsModel] = None
    avg_hour_sin: Optional[StatsModel] = None
    avg_hour_cos: Optional[StatsModel] = None

    class Config:
        from_attributes = True

# 3. The container for the different dataset statistics
class DatasetStatisticsContainerModel(BaseModel):
    train_set: Optional[DataSetStatsModel] = None
    inference_set: Optional[DataSetStatsModel] = None

    class Config:
        from_attributes = True

class ModelConfigModel(BaseModel):
    # Flexible model config for different anomly detection approaches
    model_choice: Optional[str] = None
    anomaly_sensitivity_percentile: Optional[int] = None
    lstm_sequence_length: Optional[int] = None
    
    # Can be deeply nested depending on the model
    input_features: Optional[List[str]] = None
    data_window: Optional[Dict[str, Any]] = None
    data_split: Optional[Dict[str, Any]] = None
    training_performance: Optional[Dict[str, Any]] = None
    
    # Nested statistics object
    dataset_statistics: Optional[DatasetStatisticsContainerModel] = None

    # Flexible field to accommodate other model-specific configurations
    # that are not explicitly defined above.
    additional_config: Optional[Dict[str, Any]] = Field(None, alias="features")


    class Config:
        from_attributes = True

class AnomalyDetailsModel(BaseModel):
    score: int
    raw_error: float
    threshold: float

# RENAMED from DailyProfileFeaturesModel to AnomalyFeaturesModel
class AnomalyFeaturesModel(BaseModel):
    # This model holds the feature values for the specific event/day that was anomalous.
    # Defaults are set to make the model robust against missing data from the source.
    total_appearances: Optional[int] = 0
    distinct_sites_visited: Optional[int] = 0
    distinct_zones_visited: Optional[int] = 0
    total_time_seen_hours: Optional[float] = 0.0
    critical_zone_visits: Optional[int] = 0
    restricted_zone_visits: Optional[int] = 0
    primary_site_type: Optional[str] = None
    is_single_sighting: Optional[int] = 0
    is_weekend_day: Optional[int] = 0
    num_after_hours_events: Optional[int] = 0
    avg_hour_sin: Optional[float] = 0.0
    avg_hour_cos: Optional[float] = 0.0

class ActivityLogEntryModel(BaseModel):
    sighting_start: datetime
    sighting_end: datetime
    siteId: str
    zoneId: str
    security_level: str
    cameraId: str
    
    class Config:
        populate_by_name = True

class ModelInsightModel(BaseModel):
    feature: Optional[str] = None
    # Use Union in case some features are categorical strings vs numeric
    predicted: Optional[Union[float, str, int]] = None
    actual: Optional[Union[float, str, int]] = None
    contribution_pct: Optional[float] = None

class RuleBasedEntryModel(BaseModel):
    category: str
    description: str

class ExplanationModel(BaseModel):
    alert_categories: Optional[List[str]] = []
    rule_based: Optional[List[RuleBasedEntryModel]] = []
    model_driven_insight: Optional[List[ModelInsightModel]] = None

class VisualizationModel(BaseModel):
    type: str # e.g., 'heatmap', 'line_chart'
    format: str # e.g., 'base64_png', 'plotly_json'
    data: str

class AiTriageModel(BaseModel):
    priority: str
    insight: str

# --- Main Anomaly Report Model ---
class AnomalyReportModel(BaseModel):
    id: str = Field(..., alias="_id")
    run_id: str
    # alias handles the 'model_config' from DB -> 'model_configuration' in Python
    model_configuration: Optional[Dict[str, Any]] = Field(default=None, alias='model_config')
    personId: str
    anomaly_details: AnomalyDetailsModel

    # RENAMED from 'profile_date' and made Optional and a proper datetime type
    anomaly_timestamp: Optional[datetime] = None
    
    ai_triage: Optional[AiTriageModel] = None
    explanation: Optional[ExplanationModel] = None
    
    # RENAMED from 'daily_profile_features' and made Optional
    anomaly_features: Optional[AnomalyFeaturesModel] = None
    
    # Using a flexible Dict for now, but could be strongly typed with ActivityLogEntryModel
    activity_log: Optional[List[Dict[str, Any]]] = None
    
    visualization: Optional[VisualizationModel] = None
    
    class Config:
        # Allows using field names or aliases for population
        populate_by_name = True
        # FastAPI uses this to convert non-standard types (like ObjectId) to JSON
        json_encoders = {
            'bson.objectid.ObjectId': str
        }