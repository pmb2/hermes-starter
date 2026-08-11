# Firefox MCP Tool Name Aliases

All tool names from both legacy MCP servers work with the unified `ultimate-firefox-mcp`.
This reference maps every name to its handler.

## Connection & Status

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_connect` | handle_firefox_connect | BiDi session create |
| `firefox_disconnect` | handle_firefox_disconnect | Session end |
| `firefox_status` | handle_firefox_status | Connection info |
| `firefox_ping` | handle_firefox_ping | Health check |
| `health` | handle_firefox_ping | CDP-style alias |
| `firefox_health` | handle_firefox_ping | Explicit alias |

## Browsing Contexts (Tabs)

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_list_contexts` | handle_firefox_list_contexts | Full BiDi context tree |
| `firefox_create_context` | handle_firefox_create_context | Open new tab/window |
| `firefox_close_context` | handle_firefox_close_context | Close tab/window |
| `firefox_switch_context` | handle_firefox_switch_context | Switch active context |
| `list_tabs` | handle_firefox_list_contexts | CDP-style alias |
| `close_tab` | handle_firefox_close_context | CDP-style alias |
| `new_tab` | handle_firefox_create_context | CDP-style alias |
| `select_tab` | handle_firefox_switch_context | CDP-style alias |

## Navigation

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_navigate` | handle_firefox_navigate | Navigate to URL |
| `firefox_go_back` | handle_firefox_go_back | History back |
| `firefox_go_forward` | handle_firefox_go_forward | History forward |
| `firefox_reload` | handle_firefox_reload | Reload page |
| `navigate` | handle_firefox_navigate | CDP-style alias |
| `refresh` | handle_firefox_reload | CDP-style alias |
| `navigate_history` | handle_firefox_go_back | CDP-style alias (singular) |

## Script Execution

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_evaluate_script` | handle_firefox_evaluate_script | Evaluate JS expression |
| `firefox_call_function` | handle_firefox_call_function | Call JS function |
| `firefox_evaluate_in_sandbox` | handle_firefox_evaluate_in_sandbox | Sandboxed eval |
| `firefox_evaluate_script_safe` | handle_firefox_evaluate_script_safe | Safe fallback eval |
| `evaluate_script` | handle_firefox_evaluate_script | CDP-style alias |
| `get_page_text` | _handle_get_page_text | document.body.innerText |
| `get_page_html` | _handle_get_page_html | document.documentElement.outerHTML |
| `element_text` | _handle_element_text | Element by CSS selector |

## Form Interaction

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_type_text` | handle_firefox_type_text | Type into element |
| `firefox_click_element` | handle_firefox_click_element | Click element by ref |
| `firefox_click` | handle_firefox_click | Human-like click |
| `firefox_double_click` | handle_firefox_double_click | Double click |
| `firefox_right_click` | handle_firefox_right_click | Right click |
| `firefox_hover` | handle_firefox_hover | Mouse hover |
| `firefox_move_mouse` | handle_firefox_move_mouse | Move mouse to position |
| `firefox_smooth_scroll` | handle_firefox_smooth_scroll | Smooth scroll |
| `firefox_drag` | handle_firefox_drag | Drag element |
| `firefox_perform_action_sequence` | handle_firefox_perform_action_sequence | Custom action chain |
| `firefox_set_human_input_profile` | handle_firefox_set_human_input_profile | Set timing profile |
| `fill` | handle_firefox_type_text | CDP-style alias |
| `click` | handle_firefox_click | CDP-style alias |
| `scroll` | handle_firefox_smooth_scroll | CDP-style alias |
| `wait` | _handle_wait | Sleep ms |

## Stealth & Preload Scripts

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_apply_stealth` | handle_firefox_apply_stealth | Apply all 22 measures |
| `firefox_list_stealth_measures` | handle_firefox_list_stealth_measures | List available measures |
| `firefox_add_preload_script` | handle_firefox_add_preload_script | Custom preload script |
| `firefox_remove_preload_script` | handle_firefox_remove_preload_script | Remove preload script |
| `firefox_list_preload_scripts` | handle_firefox_list_preload_scripts | List active preloads |
| `stealth_inject` | _handle_stealth_inject | Force stealth injection |
| `stealth_toggle` | _handle_stealth_toggle | Enable/disable stealth |

## Screenshots & PDF

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_take_screenshot` | handle_firefox_take_screenshot | Full page screenshot |
| `firefox_take_screenshot_element` | handle_firefox_take_screenshot_element | Element screenshot |
| `firefox_save_screenshot` | handle_firefox_save_screenshot | Screenshot to file |
| `firefox_print_to_pdf` | handle_firefox_print_to_pdf | PDF generation |
| `screenshot` | handle_firefox_take_screenshot | CDP-style alias |

## Network & Cookies

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_add_intercept` | handle_firefox_add_intercept | Add network intercept |
| `firefox_remove_intercept` | handle_firefox_remove_intercept | Remove network intercept |
| `firefox_continue_response` | handle_firefox_continue_response | Continue intercepted request |
| `firefox_fail_request` | handle_firefox_fail_request | Fail intercepted request |
| `firefox_provide_response` | handle_firefox_provide_response | Provide mock response |
| `firefox_get_cookies` | handle_firefox_get_cookies | Get cookies |
| `firefox_set_cookie` | handle_firefox_set_cookie | Set cookie |
| `firefox_delete_cookies` | handle_firefox_delete_cookies | Delete cookies |

## Events & Monitoring

| Alias | Handler | Notes |
|-------|---------|-------|
| `firefox_get_log_entries` | handle_firefox_get_log_entries | Console log entries |
| `firefox_handle_user_prompt` | handle_firefox_handle_user_prompt | Accept/dismiss dialog |
| `firefox_subscribe` | handle_firefox_subscribe | Subscribe to events |
| `firefox_unsubscribe` | handle_firefox_unsubscribe | Unsubscribe from events |
| `firefox_wait_for_event` | handle_firefox_wait_for_event | Wait for specific event |
| `firefox_wait_for_navigation` | handle_firefox_wait_for_navigation | Wait for page load |
| `firefox_wait_for_context` | handle_firefox_wait_for_context | Wait for tab creation |
| `firefox_list_realms` | handle_firefox_list_realms | List JS realms |
| `firefox_evaluate_in_realm` | handle_firefox_evaluate_in_realm | Eval in specific realm |
| `firefox_send_command` | handle_firefox_send_command | Raw BiDi/CDP command |
| `firefox_perform_actions` | handle_firefox_perform_actions | Raw input actions |
| `firefox_release_actions` | handle_firefox_release_actions | Release input actions |
