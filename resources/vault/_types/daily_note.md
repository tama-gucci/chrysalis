---
name: daily_note
version: 1
schema:
  value:
    $schema: https://json-schema.org/draft/2020-12/schema
    type: object
    additionalProperties: false
    required: []
    properties:
      type:
        const: daily_note
      date:
        type: string
        format: date
      wake_time:
        type: string
        format: date-time
      energy_level:
        type: integer
        minimum: 1
        maximum: 5
      energy_mode:
        enum:
          - optimal
          - sleep_deprived
      tags:
        type: array
        items:
          type: string
      blocks:
        type: array
        items:
          type: object
          additionalProperties: false
          required:
            - task
            - start
            - end
          properties:
            task:
              type: string
            start:
              type: string
              format: date-time
            end:
              type: string
              format: date-time
      pomodoros:
        type: array
        items:
          type: object
          additionalProperties: false
          required:
            - startTime
          properties:
            id:
              type: string
            startTime:
              type: string
              format: tasknotes-date-time
            endTime:
              type:
                - string
                - "null"
              format: tasknotes-date-time
            plannedDuration:
              type: number
              minimum: 0
            type:
              enum:
                - work
                - short-break
                - long-break
            taskPath:
              type:
                - string
                - "null"
            completed:
              type: boolean
            activePeriods:
              type: array
              items:
                type: object
                additionalProperties: false
                required:
                  - startTime
                properties:
                  startTime:
                    type: string
                    format: tasknotes-date-time
                  endTime:
                    type:
                      - string
                      - "null"
                    format: tasknotes-date-time
      timeEntries:
        type: array
        items:
          type: object
          required:
            - startTime
          additionalProperties: false
          properties:
            startTime:
              type: string
              format: tasknotes-date-time
            endTime:
              type: string
              format: tasknotes-date-time
            description:
              type: string
            duration:
              type: number
              minimum: 0
      customProperties:
        type: object
      title:
        type: string
      planning_timezone:
        type: string
      timeblocks:
        type: array
        items:
          type: object
          required: [id, title, startTime, endTime]
          additionalProperties: false
          properties:
            id: {type: string}
            title: {type: string}
            startTime: {type: string, pattern: '^(?:[01]?[0-9]|2[0-3]):[0-5][0-9]$'}
            endTime: {type: string, pattern: '^(?:(?:[01]?[0-9]|2[0-3]):[0-5][0-9]|24:00)$'}
            attachments: {type: array, items: {type: string}}
            color: {type: string}
            description: {type: string}
---
