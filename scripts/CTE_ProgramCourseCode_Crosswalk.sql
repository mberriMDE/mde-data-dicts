SELECT 2021 AS [Year]
      ,[ProgramCodeOld]
      ,[CourseCodeOld]
      ,NULL AS [ProgramTitleOld]
      ,NULL AS [CourseTitleOld]
      ,[ProgramCodeNew]
      ,[CourseCodeNew]
      ,[ProgramTitleNew]
      ,[CourseTitleNew]
  FROM [Carl_Perkins].[dbo].[ProgramCourse_XRef_2021]

UNION

SELECT 2020 AS [Year] 
      ,[ProgramCodeOld]
      ,[CourseCodeOld]
      ,NULL AS [ProgramTitleOld]
      ,NULL AS [CourseTitleOld]
      ,[ProgramCodeNew]
      ,[CourseCodeNew]
      ,[ProgramTitleNew]
      ,[CourseTitleNew]
  FROM [Carl_Perkins].[dbo].[ProgramCourse_XRef_2020]

UNION

SELECT 2019 AS [Year]
      ,[(Old) Program Code] as [ProgramCodeOld]
      ,[(OLD) Course Code] as [CourseCodeOld]
      ,[(OLD) Program Name] as [ProgramTitleOld]
      ,[(OLD) Course Title] as [CourseTitleOld]
      ,[(NEW) Program Code] as [ProgramCodeNew]
      ,[(NEW) Course Code] as [CourseCodeNew]
      ,[(NEW) Program Name] as [ProgramTitleNew]
      ,[(NEW) Course Title] as [CourseTitleNew]
  FROM [Carl_Perkins].[dbo].[ProgramCourse_XRef_2019]

UNION

SELECT 2017 AS [Year] 
      ,[ProgramCode] as [ProgramCodeOld]
      ,[(OLD) CourseCode] as [CourseCodeOld]
      ,[(OLD) Program Name] as [ProgramTitleOld]
      ,[(OLD) Course Title] as [CourseTitleOld]
      ,[ProgramCode] as [ProgramCodeNew]
      ,[(NEW) Course] as [CourseCodeNew]
      ,[Program Course Name] as [ProgramTitleNew]
      ,[(NEW) Course Title] as [CourseTitleNew]
  FROM [Carl_Perkins].[dbo].[ProgramCourse_XRef_2017]