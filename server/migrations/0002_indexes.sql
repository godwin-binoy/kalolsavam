CREATE INDEX IF NOT EXISTS idx_audit_ip_event_ts ON auth_audit(ip_hash, event, ts);
CREATE INDEX IF NOT EXISTS idx_queue_venue_status_pos ON queue_items(venue_id, status, position);
CREATE INDEX IF NOT EXISTS idx_events_day_time ON events(day, scheduled_time);
