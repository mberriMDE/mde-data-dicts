WITH
    LastDateCTE
    AS
    (
        SELECT
            t.altEdServicesTypeID value_column,
            CAST(i.incidentDate AS DATE) AS incident_date,
            ROW_NUMBER() OVER (PARTITION BY t.altEdServicesTypeID ORDER BY i.incidentDate DESC) AS rnDesc,
            ROW_NUMBER() OVER (PARTITION BY t.altEdServicesTypeID ORDER BY i.incidentDate ASC) AS rnAsc
        from dbo.altEdServicesType t
            JOIN dbo.DisciplinaryAction o ON t.altEdServicesTypeID = o.altEdServicesTypeID
            JOIN dbo.Incident i ON o.incidentid = i.incidentid
    ),
    SchoolYearCTE
    AS
    (
        SELECT
            value_column,
            incident_date,
            RIGHT(CAST(CASE WHEN MONTH(incident_date) >= 7 THEN YEAR(incident_date) ELSE YEAR(incident_date) - 1 END AS VARCHAR(4)), 2) + '-' +
        RIGHT(CAST(CASE WHEN MONTH(incident_date) >= 7 THEN YEAR(incident_date) + 1 ELSE YEAR(incident_date) END AS VARCHAR(4)), 2) AS school_year,
            rnDesc,
            rnAsc
        FROM LastDateCTE
    )
SELECT
    a.value_column,
    b.school_year AS first_school_year,
    CASE WHEN a.school_year = '23-24' THEN '' ELSE a.school_year END AS last_school_year,
    b.incident_date AS first_incident_date,
    a.incident_date AS last_incident_date
FROM SchoolYearCTE a
    JOIN SchoolYearCTE b ON (a.value_column = b.value_column) AND (a.rnDesc = 1) AND (b.rnAsc = 1)
ORDER BY a.value_column;