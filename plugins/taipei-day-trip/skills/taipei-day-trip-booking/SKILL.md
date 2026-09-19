---
name: taipei-day-trip-booking
description: Search Taipei attractions and create guided tour bookings through the Taipei Day Trip MCP server. Use when a user wants to find a Taipei attraction and reserve a morning or afternoon tour.
---

# Taipei Day Trip Booking

Use the configured Taipei Day Trip MCP server. Its protocol tool names are `search` and `add_to_cart`.

## Workflow

1. Ask for a Taipei attraction search keyword when the user has not supplied one.
2. Call `search` with the non-empty keyword.
3. Show the returned attractions. Include at least each attraction's `id` and `name`. If there are no results, ask for another keyword.
4. Ask the user to provide the selected attraction ID, visit date, and time in natural language. Do not ask the user for the price.
5. Normalize the booking before calling the tool:
   - `attractionId`: the positive integer ID selected from the search results.
   - `date`: an ISO date in `YYYY-MM-DD` format. Resolve relative dates using the user's current date and timezone. Ask a focused follow-up if the date is ambiguous.
   - `time`: convert morning expressions such as "morning", "上午", or "早上" to `morning`; convert afternoon expressions such as "afternoon", "下午", or "午後" to `afternoon`. Ask a focused follow-up if neither can be determined.
   - `price`: set to `2000` for `morning` and `2500` for `afternoon`.
6. Call `add_to_cart` with exactly these fields:

```json
{
  "attractionId": 1,
  "date": "2026-12-01",
  "time": "morning",
  "price": 2000
}
```

7. On success, show the booking confirmation and the booking page link returned by the tool so the user can complete the order. On an error response, state that the booking was not created and ask only for the information needed to retry.

Never invent an attraction ID or claim that a booking succeeded without a successful `add_to_cart` result.
