{% macro cleanup_demo_schemas(schemas=[]) %}
  {% for schema_name in schemas %}
    {% if schema_name %}
      {% do log("Dropping schema if it exists: " ~ schema_name, info=True) %}
      {% do run_query("drop database if exists " ~ schema_name ~ " cascade") %}
    {% endif %}
  {% endfor %}
{% endmacro %}
