> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tavily.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Logs

> Retrieve per-request usage logs for the API keys under your account or organization.

<Note>
  **Access to this API requires a paid plan**: an active **Paid Plan** or **PAYGO** enabled (see [Credits & Pricing](/documentation/api-credits)). Free accounts receive a `403` error.
</Note>

<Info>
  Logs never include the input or output of a request.
</Info>


## OpenAPI

````yaml POST /logs
openapi: 3.0.3
info:
  title: Tavily Search and Extract API
  description: >-
    Our REST API provides seamless access to Tavily Search, a powerful search
    engine for LLM agents, and Tavily Extract, an advanced web scraping solution
    optimized for LLMs.
  version: 1.0.0
servers:
  - url: https://api.tavily.com/
security: []
tags:
  - name: Search
  - name: Extract
  - name: Crawl
  - name: Map
  - name: Research
  - name: Usage
  - name: Logs
paths:
  /logs:
    post:
      summary: Get usage logs for your API keys
      description: >-
        Retrieve per-request usage logs for the API keys under your account or
        organization.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                limit:
                  type: integer
                  default: 10
                  minimum: 1
                  maximum: 10000
                  description: Maximum number of logs to return, most recent first.
                  example: 100
                start_date:
                  type: string
                  format: date
                  description: Inclusive start of the log window (YYYY-MM-DD).
                  example: '2026-08-01'
                end_date:
                  type: string
                  format: date
                  description: Inclusive end of the log window (YYYY-MM-DD).
                  example: '2026-08-07'
                endpoints:
                  type: array
                  items:
                    type: string
                    enum:
                      - search
                      - extract
                      - map
                      - crawl
                      - research
                  description: >-
                    Only return logs for these endpoints. By default, logs for
                    all endpoints are returned.
                  example:
                    - search
                    - research
                project_id:
                  type: string
                  description: Only return logs for a single project.
                filter_by_api_key:
                  type: boolean
                  default: false
                  description: >-
                    When `true`, return only logs for the API key provided in
                    the Authorization header. When `false` (default), logs for
                    all API keys under your account or organization are
                    returned.
      responses:
        '200':
          description: Usage logs returned successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  logs:
                    type: array
                    description: >-
                      Matching log entries, most recent first. Log entries never
                      include the input or output of the original request.
                    items:
                      type: object
                      properties:
                        timestamp:
                          type: string
                          format: date-time
                          description: When the request was made
                          example: '2026-08-06T13:14:34.739037+00:00'
                        endpoint:
                          type: string
                          enum:
                            - search
                            - extract
                            - map
                            - crawl
                            - research
                          description: Which Tavily API was called
                          example: search
                        depth:
                          type: string
                          description: >-
                            The request depth (e.g. `basic`, `advanced`). For
                            `research` requests, the model tier.
                          example: advanced
                        response_time:
                          type: number
                          description: Server-side response time in seconds
                          example: 1.52
                        credits:
                          type: number
                          description: API credits the request consumed
                          example: 2
                        api_key:
                          type: string
                          description: >-
                            The API key that made the request, masked to its
                            last 4 characters
                          example: '****abcd'
                        request_id:
                          type: string
                          description: Unique identifier of the original request
                          example: 8442d8d0-8b74-4fca-a89e-5b1b6dd33295
                  count:
                    type: integer
                    description: Number of log entries returned
                    example: 100
                  response_time:
                    type: number
                    description: Response time of this logs request in seconds
                    example: 1.33
                  request_id:
                    type: string
                    description: Unique identifier of this logs request
                    example: d98eaaf1-cf41-4234-bf23-6f1780fbcf73
        '400':
          description: Bad Request — invalid endpoints value or date range.
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: object
                    properties:
                      error:
                        type: string
              example:
                detail:
                  error: >-
                    Invalid endpoints: news. Valid endpoints are: search,
                    extract, map, crawl, research
        '401':
          description: Unauthorized - Your API key is wrong or missing.
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: object
                    properties:
                      error:
                        type: string
              example:
                detail:
                  error: 'Unauthorized: missing or invalid API key.'
        '403':
          description: Forbidden — usage logs are only available to paying customers.
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: object
                    properties:
                      error:
                        type: string
              example:
                detail:
                  error: >-
                    Access denied. Usage logs are only available to paying
                    customers. Please upgrade your plan to access this feature.
        '429':
          description: Too Many Requests
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: object
                    properties:
                      error:
                        type: string
              example:
                detail:
                  error: >-
                    Your request has been blocked due to excessive requests.
                    Please reduce the rate of requests
        '504':
          description: Gateway Timeout — the logs query timed out.
          content:
            application/json:
              schema:
                type: object
                properties:
                  detail:
                    type: object
                    properties:
                      error:
                        type: string
              example:
                detail:
                  error: >-
                    Request timed out while fetching usage logs. Please contact
                    our team at support@tavily.com.
      security:
        - bearerAuth: []
      x-codeSamples: []
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      description: >-
        Bearer authentication header in the form Bearer <token>, where <token>
        is your Tavily API key (e.g., Bearer tvly-YOUR_API_KEY).

````