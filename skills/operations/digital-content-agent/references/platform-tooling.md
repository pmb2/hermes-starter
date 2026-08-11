# Platform Tooling API Reference

Key API details for each platform tool module in `tools/`.

## Reddit (`tools/reddit_tool.py`)
- **Library**: PRAW (pip install praw)
- **Credentials needed**: client_id, client_secret, username, password
- **Credential source**: https://www.reddit.com/prefs/apps (create "script" app)
- **User agent format**: `DigitalContentAgent/1.0 (by /u/YourUsername)`
- **Rate limit**: 60 requests/minute (PRAW auto-handles this)
- **Key methods**: submit_text_post(), submit_link_post(), submit_image_post(), reply_to_post(), monitor_subreddit(), search_subreddit(), get_post_performance(), find_target_subreddits()
- **Free posting**: Unlimited — no cost per post
- **Optimal times**: Weekdays 7am/12pm/6pm ET, Weekends 9am/2pm/8pm ET
- **Max daily posts**: 3-5 (more gets flagged)
- **Subreddit discovery**: Use find_target_subreddits(keywords=[...], min_subscribers=1000)

## Pinterest (`tools/pinterest_tool.py`)
- **API version**: v5
- **Credentials needed**: access_token (OAuth 2.0)
- **Credential source**: https://developers.pinterest.com/
- **Rate limit**: 100 requests/minute (v5 API)
- **Key methods**: create_pin(), list_boards(), create_board(), get_pin_analytics(), bulk_create_pins(), search_pins(), create_ideal_board_structure()
- **Free tier**: Yes — API is free with developer app
- **Optimal times**: Daily 2am/8am/2pm/8pm ET
- **Max daily pins**: 15-25
- **Pin dimensions**: 1000×1500px (2:3 ratio) ideal
- **Board structure**: Create 8 boards per niche (Tips, Strategies, Downloads, Beginners, Inspiration, Free Resources, Templates, Success Stories)

## Quora (`tools/quora_tool.py`)
- **Method**: Browser automation via Playwright
- **Install**: pip install playwright && playwright install chromium
- **Credentials**: email + password (standard login)
- **Key methods**: login(), answer_question(), search_questions(), find_high_opportunity_questions(), get_answer_performance()
- **Session**: Must call login() first each session
- **Human-like typing**: Chunks text into 500-char segments with delays
- **Optimal times**: Weekdays 8am/1pm/5pm ET, Weekends 9am/3pm/8pm ET
- **Max daily answers**: 3-5 (to avoid spam detection)
- **Strategy**: Answer questions with 100+ followers and few existing answers

## TikTok (`tools/tiktok_tool.py`)
- **Method**: Content Posting API (business) + Playwright fallback
- **Credentials needed**: access_token, client_key, client_secret (Business API)
- **Credential source**: https://developers.tiktok.com/ (requires Business account + app approval)
- **Fallback**: upload_video_browser() uses Playwright when API not available
- **Key methods**: upload_video(), upload_video_browser(), get_video_analytics(), get_account_stats(), get_trending_hashtags()
- **Rate limit**: Varies by API tier
- **Optimal times**: Mon 7am/12pm/7pm, Tue 8am/2pm/8pm, Wed 9am/1pm/9pm, Thu 7am/12pm/6pm, Fri 6am/11am/5pm, Sat 9am/2pm/8pm, Sun 10am/3pm/9pm
- **Max daily uploads**: 1-3
- **Trending hashtags**: digitalproducts (2.5B), digitalmarketing (1.8B), passiveincome (3.2B), sidehustle (1.5B), printables (850M)

## Facebook (`tools/facebook_tool.py`)
- **API version**: v19.0 (Graph API)
- **Credentials needed**: access_token (long-lived page token)
- **Credential source**: https://developers.facebook.com/ (App + Page API permissions)
- **Key methods**: post_to_page(), post_to_group(), get_pages(), get_groups(), get_page_insights(), get_post_engagement(), get_comments(), reply_to_comment()
- **Rate limit**: 200 calls/hour per user
- **Optimal times**: Weekdays 9am/1pm/3pm ET, Weekends 10am/2pm/8pm ET
- **Max daily posts**: 3-5 per page, 1-2 per group
- **Page token**: Long-lived (60 days), use _get_page_token() for page-specific tokens
- **Ads**: Not supported via this tool (requires Marketing API)

## Gumroad (`tools/gumroad_tool.py`)
- **API base**: https://api.gumroad.com/v2
- **Credentials needed**: access_token
- **Credential source**: https://app.gumroad.com/settings/advanced
- **Key methods**: create_product(), list_products(), get_product(), update_product(), get_sales(), get_total_revenue(), list_affiliates(), add_affiliate(), enable_affiliate_program(), create_variant()
- **Rate limit**: 1000 requests/hour
- **Fees**: 0% monthly + 10% per sale (free tier) OR $10/month + 0% per sale (premium)
- **Price format**: All prices in cents (e.g. $19.99 = 1999 cents)
- **Affiliate program**: Built-in, set commission_percent (20-30% recommended)
- **Variants**: Use create_variant_category() then create_variant() for options like "Format: PDF/Notion"
- **Sales data**: get_sales() returns email, price, date, refund status, affiliate info
