-- Show core runtime configuration and HEDIS activation profile.

SELECT config_key, config_value, updated_by, updated_at
FROM system_config
WHERE config_key IN (
  'hedis.measure_profile',
  'hedis.assume_enrolled_if_missing'
)
ORDER BY config_key;

SELECT COUNT(*) AS active_measure_definitions
FROM hedis_measure_definitions
WHERE is_active = TRUE;

SELECT COUNT(*) AS active_valuesets
FROM hedis_valuesets
WHERE is_active = TRUE;
