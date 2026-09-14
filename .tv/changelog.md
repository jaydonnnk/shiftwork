> ## Documentation Index
> Fetch the complete documentation index at: https://docs.tavily.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Changelog

<AccordionGroup>
  <Accordion title="Boosted domains for Search" icon="rocket" description="August 2026">
    <b><br />New [<code>include\_domains\_mode</code>](/documentation/api-reference/endpoint/search#body-include-domains-mode) parameter for [Search](/documentation/api-reference/endpoint/search)</b><br />

    <ul>
      <li>
        <b><code>include\_domains\_mode</code></b> — controls how <code>include\_domains</code> is applied. Set to <b><code>"boost"</code></b> to also search the rest of the web, so results outside <code>include\_domains</code> can still surface, rather than excluding them, or <b><code>"filter"</code></b> to keep the existing hard-filter behavior. Requires <code>include\_domains</code> to be set, or the request returns a <code>400</code>.
      </li>

      <li>
        See <a href="/documentation/best-practices/best-practices-search#by-domain">Best Practices for Search</a> for guidance on when to boost trusted domains vs. hard-filter to them.
      </li>

      <li>
        <b>Supported domain types:</b> plain domains and subdomains (e.g. <code>nytimes.com</code>, <code>cooking.nytimes.com</code>), with or without a protocol/<code>[www](http://www).</code> prefix. Wildcards, regex, and URLs with a path/query/fragment are not supported.
      </li>

      <li>
        <b>Hard-filter matching:</b> under <code>include\_domains\_mode="filter"</code> and for <code>exclude\_domains</code>, listing a domain (e.g. <code>nytimes.com</code>) matches that domain and all its subdomains, while listing a subdomain (e.g. <code>cooking.nytimes.com</code>) matches only that exact host.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Safe search for everyone" icon="rocket" description="August 2026">
    <b><br />[<code>safe\_search</code>](/documentation/api-reference/endpoint/search#body-safe-search) is now available on all plans</b><br />

    <ul>
      <li>
        Set <b><code>"safe\_search": true</code></b> in your [Search](/documentation/api-reference/endpoint/search) request to drop adult and unsafe content from results and images. Defaults to <code>false</code>. Not supported for <code>fast</code> or <code>ultra-fast</code> search depths.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Language boosting and filtering for Search" icon="rocket" description="August 2026">
    <b><br />New [<code>language</code>](/documentation/api-reference/endpoint/search#body-language) and [<code>filter\_by\_language</code>](/documentation/api-reference/endpoint/search#body-filter-by-language) parameters for [Search](/documentation/api-reference/endpoint/search)</b><br />

    <ul>
      <li>
        <b><code>language</code></b> — boost search results in a specific language. Accepts an ISO 639-1 code (e.g. <code>en</code>, <code>fr</code>, <code>zh-cn</code>) or an English language name (e.g. <code>english</code>, <code>french</code>).
      </li>

      <li>
        <b><code>filter\_by\_language</code></b> — when <code>true</code>, strictly drops results that don't match <code>language</code> instead of only boosting them in ranking. Requires <code>language</code> to be set, or the request returns a <code>400</code>.
      </li>

      <li>
        See <a href="/documentation/best-practices/best-practices-search#by-language">Best Practices for Search</a> for guidance on when to use a soft boost vs. a strict filter.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Logs API: filter by API key and Research endpoint" icon="rocket" description="August 2026">
    <b><br />The [Logs endpoint](/documentation/api-reference/endpoint/logs) can now return logs for the calling API key only, and filter by the Research endpoint</b><br />

    <ul>
      <li>
        <b><code>filter\_by\_api\_key</code></b> — when <code>true</code>, only logs for the API key provided in the Authorization header are returned, instead of logs for all API keys under your account or organization.
      </li>

      <li>
        <b>Type:</b> <code>boolean</code>
      </li>

      <li>
        <b>Default:</b> <code>false</code>
      </li>

      <li>
        <b><code>research</code></b> is now a valid value in the <code>endpoints</code> filter, alongside <code>search</code>, <code>extract</code>, <code>map</code>, and <code>crawl</code>.
      </li>

      <li>
        The Logs API is available on paid plans and is now fully documented in the <a href="/documentation/api-reference/endpoint/logs">API reference</a>.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Chunked content for basic search" icon="rocket" description="July 2026">
    <b><br />[<code>search\_depth=basic</code>](/documentation/api-reference/endpoint/search#body-search-depth) now returns reranked chunks, and [<code>chunks\_per\_source</code>](/documentation/api-reference/endpoint/search#body-chunks-per-source) applies to it</b><br />

    <ul>
      <li>
        <b>Basic search now returns chunks.</b> <code>search\_depth=basic</code> previously returned a single page summary per source. It now returns multiple semantically relevant snippets per URL, so <code>results\[].content</code> may contain several chunks joined by <code>\[...]</code>.
      </li>

      <li>
        <b><code>chunks\_per\_source</code> now applies to <code>basic</code>.</b> It previously affected <code>advanced</code> and <code>fast</code>, and now controls the number of chunks returned per source at those depths plus <code>basic</code>.
      </li>

      <li>
        <b>Choosing between the depths.</b> <code>advanced</code> still offers broader coverage and the highest relevance at higher latency. See <a href="/documentation/best-practices/best-practices-search#basic-vs-advanced">basic vs advanced</a>.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Session tracking headers" icon="rocket" description="May 2026">
    <b><br />Attach session and end-user identifiers to your API requests — see <a href="/documentation/api-reference/introduction#session--user-tracking">Session Tracking</a></b><br />

    <ul>
      <li>
        Optionally tag any Tavily API request with HTTP headers so requests can be attributed back to a session or an end-user.
      </li>

      <li>
        <b><code>X-Session-Id</code></b> — opaque identifier for a session of related requests (e.g. all calls from one user conversation).
      </li>

      <li>
        <b><code>X-Human-Id</code></b> — opaque identifier for the end-user behind the request. Useful when a single API key serves many human users.
      </li>

      <li>
        Populated automatically when using the <a href="/documentation/mcp">Tavily MCP server</a> — local MCP generates a per-process session ID and forwards <code>HUMAN\_ID</code>; remote MCP derives the session ID from the MCP <code>initialize</code> handshake.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Domain filtering and output length for Research" icon="rocket" description="May 2026">
    <b><br />[<code>include\_domains</code>](/documentation/api-reference/endpoint/research#body-include-domains), [<code>exclude\_domains</code>](/documentation/api-reference/endpoint/research#body-exclude-domains), and [<code>output\_length</code>](/documentation/api-reference/endpoint/research#body-output-length) parameters for [Research](/documentation/api-reference/endpoint/research)</b><br />

    <ul>
      <li>
        <b><code>include\_domains</code></b><br />

        <ul>
          <li><b>Type:</b> <code>array</code> of <code>string</code></li>
          <li><b>Default:</b> <code>\[]</code> — <b>Max:</b> 20 entries</li>
          <li>Soft preference for sources. The research agent prioritizes these domains, but URLs from other domains can still appear in the final report.</li>
          <li>Matching is host-based and includes subdomains (e.g. <code>sec.gov</code> matches <code>sec.gov</code> and <code>data.sec.gov</code>).</li>
        </ul>
      </li>

      <li>
        <b><code>exclude\_domains</code></b><br />

        <ul>
          <li><b>Type:</b> <code>array</code> of <code>string</code></li>
          <li><b>Default:</b> <code>\[]</code> — <b>Max:</b> 20 entries</li>
          <li>Hard blocklist. No URL from a listed domain or any of its subdomains appears in the response.</li>
          <li>Subdomain matching is downward only — blocking <code>medium.com</code> also blocks <code>blog.medium.com</code>, but blocking <code>blog.medium.com</code> leaves <code>medium.com</code> itself allowed.</li>
        </ul>
      </li>

      <li>
        <b><code>output\_length</code></b><br />

        <ul>
          <li><b>Type:</b> <code>string</code></li>
          <li><b>Options:</b> <code>short</code>, <code>standard</code>, <code>long</code></li>
          <li><b>Default:</b> <code>standard</code></li>
          <li>Typed control over response size. Ranges are targets, not hard caps — individual responses can fall outside when the question requires it.</li>
        </ul>
      </li>
    </ul>
  </Accordion>

  <Accordion title="Enterprise API key management endpoints" icon="rocket" description="March 2026">
    <b><br />Enterprise API key management — [Generate Keys](/documentation/enterprise/generate-keys), [Deactivate Keys](/documentation/enterprise/deactivate-keys), [Key Info](/documentation/enterprise/key-info)</b><br />

    <ul>
      <li>
        Enterprise users can programmatically manage API keys via dedicated endpoints.
      </li>

      <li>
        <b>[POST /generate-keys](/documentation/enterprise/generate-keys)</b> — Generate new API keys for your organization.
      </li>

      <li>
        <b>[POST /deactivate-keys](/documentation/enterprise/deactivate-keys)</b> — Deactivate existing API keys.
      </li>

      <li>
        <b>[GET /key-info](/documentation/enterprise/key-info)</b> — Retrieve information about an existing API key.
      </li>

      <li>
        These endpoints are available on the <b>Enterprise plan only</b>. [Talk to an expert](https://tavily.com/enterprise) to learn more.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Exact match parameter" icon="rocket" description="February 2026">
    <b><br /><code>exact\_match</code> parameter for [Search](/documentation/api-reference/endpoint/search#body-exact-match)</b><br />

    <ul>
      <li>
        Use <code>exact\_match</code> to ensure that only search results containing the exact quoted phrase(s) in your query are returned, bypassing synonyms or semantic variations.
      </li>

      <li>
        Wrap target phrases in quotes within your query (e.g. <code>"John Smith" CEO Acme Corp</code>).
      </li>

      <li>
        <b>Type:</b> <code>boolean</code>
      </li>

      <li>
        <b>Default:</b> <code>false</code>
      </li>

      <li>
        Because this narrows retrieval, it may return fewer results or empty result fields when no exact matches are found.
      </li>

      <li>
        Best suited for due diligence, data enrichment, and legal/compliance use cases where verbatim matches are required.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Project tracking with X-Project-ID header" icon="rocket" description="January 2026">
    <b><br />Track API usage by project with the new <code>X-Project-ID</code> header</b><br />

    <ul>
      <li>
        You can now attach a Project ID to your API requests to organize and track usage by project. This is useful when a single API key is used across multiple projects or applications.
      </li>

      <li>
        <b>HTTP Header:</b> Add <code>X-Project-ID: your-project-id</code> to any API request
      </li>

      <li>
        <b>Python SDK:</b> Pass <code>project\_id="your-project-id"</code> when instantiating the client, or set the <code>TAVILY\_PROJECT</code> environment variable
      </li>

      <li>
        <b>JavaScript SDK:</b> Pass <code>projectId: "your-project-id"</code> when instantiating the client, or set the <code>TAVILY\_PROJECT</code> environment variable
      </li>

      <li>
        An API key can be associated with multiple projects
      </li>

      <li>
        Filter requests by project in the [/usage endpoint](/documentation/api-reference/endpoint/usage) and platform usage dashboard to keep track of where requests originate from
      </li>
    </ul>
  </Accordion>

  <Accordion title="New search_depth options fast and ultra-fast (BETA)" icon="rocket" description="December 2025">
    <b><br />[<code>search\_depth</code> parameter](/documentation/api-reference/endpoint/search#body-search-depth) - New options: <code>fast</code> and <code>ultra-fast</code></b><br />

    <ul>
      <li>
        <b><code>fast</code> (BETA)</b><br />

        <ul>
          <li>Optimized for low latency while maintaining high relevance to the user query</li>
          <li><b>Cost:</b> 1 API Credit</li>
        </ul>
      </li>

      <li>
        <b><code>ultra-fast</code> (BETA)</b><br />

        <ul>
          <li>Optimized strictly for latency</li>
          <li><b>Cost:</b> 1 API Credit</li>
        </ul>
      </li>
    </ul>
  </Accordion>

  <Accordion title="Intent Based Extraction" icon="rocket" description="December 2025">
    <b><br />[<code>query</code>](/documentation/api-reference/endpoint/extract#body-query) and [<code>chunks\_per\_source</code>](/documentation/api-reference/endpoint/extract#body-chunks-per-source) parameters for Extract and Crawl</b><br />

    <ul>
      <li>
        <b><code>query</code> (Extract)</b><br />

        <ul>
          <li><b>Type:</b> <code>string</code></li>
          <li>User intent for reranking extracted content chunks. When provided, chunks are reranked based on relevance to this query.</li>
        </ul>
      </li>

      <li>
        <b><code>chunks\_per\_source</code> (Extract & Crawl)</b><br />

        <ul>
          <li><b>Type:</b> <code>integer</code></li>
          <li><b>Range:</b> 1 to 5</li>
          <li><b>Default:</b> 3</li>
          <li>Chunks are short content snippets (maximum 500 characters each) pulled directly from the source.</li>
          <li>Use <code>chunks\_per\_source</code> to define the maximum number of relevant chunks returned per source and to control the <code>raw\_content</code> length.</li>
          <li>Chunks will appear in the <code>raw\_content</code> field as: <code>\<chunk 1> \[...] \<chunk 2> \[...] \<chunk 3></code>.</li>
          <li>Available only when <code>query</code> is provided (Extract) or <code>instructions</code> are provided (Crawl).</li>
        </ul>
      </li>
    </ul>
  </Accordion>

  <Accordion title="Include usage parameter" icon="rocket" description="December 2025">
    <b><br />[<code>include\_usage</code> parameter](/documentation/api-reference/endpoint/search#body-include-usage)</b><br />

    <ul>
      <li>
        You can now include credit usage information in the API response for the [Search](/documentation/api-reference/endpoint/search#body-include-usage), [Extract](/documentation/api-reference/endpoint/extract#body-include-usage), [Crawl](/documentation/api-reference/endpoint/crawl#body-include-usage), and [Map](/documentation/api-reference/endpoint/map#body-include-usage) endpoints.
      </li>

      <li>
        Set the <code>include\_usage</code> parameter to <code>true</code> to receive credit usage information in the API response.
      </li>

      <li>
        <b>Type:</b> <code>boolean</code>
      </li>

      <li>
        <b>Default:</b> <code>false</code>
      </li>

      <li>
        When enabled, the response includes a <code>usage</code> object with <code>credits</code> information, making it easy to track API credit consumption for each request.
      </li>

      <li>
        <b>Note:</b> The value may be 0 if the total successful calls have not yet reached the minimum threshold. See our [Credits & Pricing documentation](/documentation/api-credits) for details.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Vercel AI SDK v5 integration" icon="rocket" description="November 2025">
    <b><br />[Tavily is now integrated with Vercel AI SDK v5](/documentation/integrations/vercel)</b><br />

    <ul>
      <li>
        We've released a new [<code>@tavily/ai-sdk</code>](https://www.npmjs.com/package/@tavily/ai-sdk) package that provides pre-built AI SDK tools for Vercel's AI SDK v5.
      </li>

      <li>
        Easily add real-time web search, content extraction, intelligent crawling, and site mapping to your AI SDK project with ready-to-use tools.
      </li>

      <li>
        <b>Available Tools:</b> <code>tavilySearch</code>, <code>tavilyExtract</code>, <code>tavilyCrawl</code>, and <code>tavilyMap</code>
      </li>

      <li>
        Full TypeScript support with proper type definitions and seamless integration with Vercel AI SDK v5.
      </li>

      <li>
        Check out our [ integration guide](/documentation/integrations/vercel) to get started.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Crawl & Map timeout parameter" icon="rocket" description="November 2025">
    <b><br />[<code>timeout</code> parameter for Crawl](/documentation/api-reference/endpoint/crawl#body-timeout) and [<code>timeout</code> parameter for Map](/documentation/api-reference/endpoint/map#body-timeout)</b><br />

    <ul>
      <li>
        You can now specify a custom timeout for the [Crawl](/documentation/api-reference/endpoint/crawl) and [Map](/documentation/api-reference/endpoint/map) endpoints to control how long to wait for the operation before timing out.
      </li>

      <li>
        <b>Type:</b> <code>float</code>
      </li>

      <li>
        <b>Range:</b> Between 10 and 150 seconds
      </li>

      <li>
        <b>Default:</b> 150 seconds
      </li>

      <li>
        This gives you fine-grained control over crawl and map operation timeouts, allowing you to balance between reliability and speed based on your specific use case.
      </li>
    </ul>
  </Accordion>

  <Accordion title="New team roles & permissions" icon="rocket" description="August 2025">
    <p /><b>Role options: Owner, Admin, Member</b>
    <p />You can now assign roles to team members, giving you more control over access and permissions. Each team has one owner, while there can be multiple admins and multiple members.
    The key distinction between roles is in their permissions for Billing and Settings:<p />

    <ul>
      <li>
        <b>Owner</b><br />

        <ul>
          <li>Full access to all Settings</li>
          <li>Access and ownership of the Billing account</li>
        </ul>
      </li>

      <li>
        <b>Admin</b><br />

        <ul>
          <li>Full access to Settings except ownership transfer</li>
          <li>No access to Billing</li>
        </ul>
      </li>

      <li>
        <b>Member</b><br />

        <ul>
          <li>Limited Settings access (view members only)</li>
          <li>No access to Billing</li>
        </ul>
      </li>
    </ul>
  </Accordion>

  <Accordion title="Extract timeout parameter" icon="rocket" description="August 2025">
    <b><br />[<code>timeout</code> parameter](/documentation/api-reference/endpoint/extract#body-timeout)</b><br />

    <ul>
      <li>
        You can now specify a custom timeout for the [Extract](/documentation/api-reference/endpoint/extract) endpoint to control how long to wait for URL extraction before timing out.
      </li>

      <li>
        <b>Type:</b> <code>number</code> (float)
      </li>

      <li>
        <b>Range:</b> Between 1.0 and 60.0 seconds
      </li>

      <li>
        <b>Default behavior:</b> If not specified, automatic timeouts are applied based on <code>extract\_depth</code>: 10 seconds for basic extraction and 30 seconds for advanced extraction.
      </li>

      <li>
        This gives you fine-grained control over extraction timeouts, allowing you to balance between reliability and speed based on your specific use case.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Start date & end date Parameters" icon="rocket" description="July 2025">
    <b><br />[<code>start\_date</code> parameter](/documentation/api-reference/endpoint/search#body-start_date),[<code>end\_date</code> parameter](/documentation/api-reference/endpoint/search#body-end-date)</b><br />

    <ul>
      <li>
        You can now use both the <code>start\_date</code> and <code>end\_date</code> parameters in the [Search](/documentation/api-reference/endpoint/search) endpoints.
      </li>

      <li>
        <code>start\_date</code> will return all results after the specified start date. Required to be written in the format YYYY-MM-DD.
      </li>

      <li>
        <code>end\_date</code> will return all results before the specified end date. Required to be written in the format YYYY-MM-DD.
      </li>

      <li>
        Set <code>start\_date</code> to <code>2025-01-01</code> and <code>end\_date</code> to <code>2025-04-01</code> to reiceive results strictly from this time range.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Usage dashboard" icon="rocket" description="July 2025">
    <b><br />[Login to your account to view the usage dashboard](https://www.tavily.com/)</b><br />
    <br />The usage dashboard provides the following features to paid users/teams:<br />

    <ul>
      <li>
        The Usage Graph offers a breakdown of daily usage across all Tavily endpoints with historical data to enable month over month usage and spend comparison.
      </li>

      <li>
        The Logs Table offers granular insight into each API request to ensure visibility and traceability with every Tavily interaction.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Include favicon parameter" icon="rocket" description="June 2025">
    <b><br />[<code>include\_favicon</code> parameter](/documentation/api-reference/endpoint/search#body-include-favicon)</b><br />

    <ul>
      <li>
        You can now include the favicon URL for each result in the [Search](/documentation/api-reference/endpoint/search), [Extract](/documentation/api-reference/endpoint/extract), and [Crawl](/documentation/api-reference/endpoint/crawl) endpoints.
      </li>

      <li>
        Set the <code>include\_favicon</code> parameter to <code>true</code> to receive the favicon URL (if available) for each result in the API response.
      </li>

      <li>
        This makes it easy to display website icons alongside your search, extraction, or crawl results, improving the visual context and user experience in your application.
      </li>
    </ul>
  </Accordion>

  <Accordion title="Auto parameters" icon="rocket" description="June 2025">
    <b>Tavily Search<br />[<code>auto\_parameters</code>](/documentation/api-reference/endpoint/search#body-auto-parameters)</b><br />

    <ul>
      <li><b>Boolean default:</b> <code>false</code></li>
      <li>When <code>auto\_parameters</code> is enabled, Tavily automatically configures search parameters based on your query's content and intent. You can still set other parameters manually, and your explicit values will override the automatic ones.</li>
      <li>The parameters <code>include\_answer</code>, <code>include\_raw\_content</code>, and <code>max\_results</code> must always be set manually, as they directly affect response size.</li>
      <li><b>Note:</b> <code>search\_depth</code> may be automatically set to <code>advanced</code> when it's likely to improve results. This uses <b>2 API credits per request</b>. To avoid the extra cost, you can explicitly set <code>search\_depth</code> to <code>basic</code>.</li>
    </ul>
  </Accordion>

  <Accordion title="Usage endpoint" icon="rocket" description="May 2025">
    <b>[<code>/usage</code> endpoint](/documentation/api-reference/endpoint/usage)</b><br />

    <ul>
      <b>Easily check your API usage and plan limits.</b><br />Just <code>GET [https://api.tavily.com/usage](https://api.tavily.com/usage)</code> with your API key to monitor your account in real time.
    </ul>
  </Accordion>

  <Accordion title="Country parameter" icon="rocket" description="May 2025">
    <b>Tavily Search<br />[<code>country</code> parameter](/documentation/api-reference/endpoint/search#body-country)<br /><p>Boost search results from a specific country.</p></b>

    <ul>
      This will prioritize content from the selected country in the search results. Available only if <code>topic</code> is <code>general</code>.
    </ul>
  </Accordion>

  <Accordion title="Make & n8n integrations" icon="rocket" description="May 2025">
    <b>Make & n8n Integrations</b><br />

    <ul>
      <li>
        <b>[Tavily is now available for no-code integration through n8n.](/documentation/integrations/n8n)</b><br />
        <p>Integrate Tavily with n8n to enhance your workflows with real-time web search and content extraction—without writing code. With Tavily's powerful search and extraction capabilities, you can seamlessly integrate up-to-date online information into your n8n automations.</p>
      </li>

      <li>
        <b>[Integrate Tavily with Make without writing a single line of code.](/documentation/integrations/make)</b><br />
        <p>With Tavily's powerful search and content extraction capabilities, you can seamlessly integrate real-time online information into your Make workflows and automations.</p>
      </li>
    </ul>
  </Accordion>

  <Accordion title="Markdown format" icon="rocket" description="May 2025">
    <b>Tavily Extract<br />[<code>format</code> parameter](/documentation/api-reference/endpoint/extract#body-format)</b>

    <ul>
      <li><b>Type:</b> <code>enum\<string></code></li>
      <li><b>Default:</b> <code>markdown</code></li>
      <li>The format of the extracted web page content. <code>markdown</code> returns content in markdown format. <code>text</code> returns plain text and may increase latency.</li>
      <li><b>Available options:</b> <code>markdown</code>, <code>text</code></li>
    </ul>
  </Accordion>

  <Accordion title="Advanced search & chunks per source" icon="rocket" description="April 2025">
    <b>Tavily Search<br />[<code>search\_depth</code>](/documentation/api-reference/endpoint/search#body-search-depth) and [<code>chunks\_per\_source</code>](/documentation/api-reference/endpoint/search#body-chunks-per-source)parameters</b>

    <ul>
      <li>
        <b><code>search\_depth</code></b><br />

        <ul>
          <li><b>Type:</b> <code>enum\<string></code></li>
          <li><b>Default:</b> <code>basic</code></li>
          <li>The depth of the search. <code>advanced</code> search is tailored to retrieve the most relevant sources and content snippets for your query, while <code>basic</code> search provides generic content snippets from each source.</li>
          <li>A <code>basic</code> search costs 1 API Credit, while an <code>advanced</code> search costs 2 API Credits.</li>
          <li><b>Available options:</b> <code>basic</code>, <code>advanced</code></li>
        </ul>
      </li>

      <li>
        <b><code>chunks\_per\_source</code></b><br />

        <ul>
          <li>Chunks are short content snippets (maximum 500 characters each) pulled directly from the source.</li>
          <li>Use <code>chunks\_per\_source</code> to define the maximum number of relevant chunks returned per source and to control the content length.</li>
          <li>Chunks will appear in the content field as: <code>\<chunk 1> \[...] \<chunk 2> \[...] \<chunk 3></code>.</li>
          <li>Available only when <code>search\_depth</code> is <code>advanced</code>.</li>
          <li><b>Required range:</b> <code>1 \< x \< 3</code></li>
        </ul>
      </li>
    </ul>
  </Accordion>

  <Accordion title="Tavily crawl (BETA)" icon="rocket" description="April 2025">
    [Tavily Crawl](https://docs.tavily.com/documentation/api-reference/endpoint/crawl)<br />

    <ul>
      <li>
        Tavily Crawl enables you to traverse a website like a graph, starting from a base URL and automatically discovering and extracting content from multiple linked pages. With Tavily Crawl, you can:

        <ul>
          <li>Specify the starting URL and let the crawler intelligently follow links to map out the site structure.</li>
          <li>Control the depth and breadth of the crawl, allowing you to focus on specific sections or perform comprehensive site-wide analysis.</li>
          <li>Apply filters and custom instructions to target only the most relevant pages or content types.</li>
          <li>Aggregate extracted content for further analysis, reporting, or integration into your workflows.</li>
          <li>Seamlessly integrate with your automation tools or use the API directly for flexible, programmatic access.</li>
        </ul>

        Tavily Crawl is ideal for use cases such as large-scale content aggregation, competitive research, knowledge base creation, and more.<br />
        For full details and API usage examples, see the [Tavily Crawl API reference](https://docs.tavily.com/documentation/api-reference/endpoint/crawl).
      </li>
    </ul>
  </Accordion>
</AccordionGroup>
