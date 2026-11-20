# All tests (Bazzite Console Suite)

Every test of the suite, by test folder: the test file, the test, how many cases a parametrized test runs, the time it took when that was 0.1 s or more, and what it checks (its docstring's first sentence, else its name). `tools/all_tests.py` writes this page from the tests, and CI fails when it is not the list of the tests as they are. The cases and the times are of one local pytest run of each folder (`tools/all_tests.py --run`), without the container and package setup each CI job has first; a test added since has none yet.

2856 test functions (3244 cases counting the parametrized ones) in 34 test folders, and 35 installer tests.

## Summary

| Test folder | Files | Tests | Time |
|---|---|---|---|
| [apps/bluetooth](#appsbluetooth) | 3 | 34 | 0.4 s |
| [apps/board](#appsboard) | 3 | 28 | 1.8 s |
| [apps/cec](#appscec) | 6 | 54 | 0.7 s |
| [apps/clb](#appsclb) | 13 | 90 | 2.8 s |
| [apps/compute](#appscompute) | 5 | 31 |  |
| [apps/controller](#appscontroller) | 13 | 164 | 5.8 s |
| [apps/cores](#appscores) | 4 | 29 |  |
| [apps/datstation](#appsdatstation) | 7 | 39 | 2.1 s |
| [apps/fan](#appsfan) | 2 | 37 | 0.4 s |
| [apps/overlay](#appsoverlay) | 2 | 18 | 0.2 s |
| [apps/password](#appspassword) | 2 | 22 | 0.4 s |
| [apps/pcsx2](#appspcsx2) | 14 | 141 | 19.0 s |
| [apps/ppsspp](#appsppsspp) | 11 | 91 | 4.5 s |
| [apps/quickfix](#appsquickfix) | 6 | 38 |  |
| [apps/remoteplay](#appsremoteplay) | 25 | 240 | 9.6 s |
| [apps/rpcs3](#appsrpcs3) | 12 | 114 | 5.6 s |
| [apps/sftp](#appssftp) | 11 | 86 | 5.6 s |
| [apps/shadps4](#appsshadps4) | 17 | 147 | 7.7 s |
| [apps/ssd](#appsssd) | 4 | 50 | 0.8 s |
| [apps/upscaler](#appsupscaler) | 10 | 98 | 1.6 s |
| [apps/vita3k](#appsvita3k) | 9 | 72 | 4.9 s |
| [apps/webcam](#appswebcam) | 12 | 113 | 2.5 s |
| [apps/xenia](#appsxenia) | 8 | 67 | 4.2 s |
| [core](#core) | 25 | 174 | 3.5 s |
| [dev/dash](#devdash) | 6 | 50 | 2.3 s |
| [dev/demo](#devdemo) | 3 | 32 | 0.4 s |
| [dev/deps](#devdeps) | 6 | 102 | 2.1 s |
| [dev/itests](#devitests) | 1 | 15 | 0.3 s |
| [dev/nrt](#devnrt) | 4 | 123 | 23.1 s |
| [dev/sounds](#devsounds) | 2 | 22 | 0.6 s |
| [dev/studio](#devstudio) | 6 | 58 |  |
| [dev/text](#devtext) | 5 | 44 |  |
| [portal](#portal) | 17 | 217 | 30.2 s |
| [tools](#tools) | 37 | 216 | 10.2 s |
| **All** | | **2856** | **153 s** |

The pytest runs together take the time above. The rest of a local CI run is the setup of each job (a container, Python 3.12 and the job's own packages, once per test folder) and the jobs that are not pytest: the installer tests, the shell checks (shellcheck), the native build (FFmpeg) and the wiki. A push runs the jobs of what it changed, not all of them.

## Installer tests

`tools/installer-tests/`, one per app and the portal; CI runs the ones of what a push changed, side by side.

| Script | What it checks |
|---|---|
| `bluetooth.sh` | Exercise apps/bluetooth/install.sh. |
| `board.sh` | Exercise apps/board/install.sh. |
| `cec.sh` | Exercise apps/cec/install.sh. |
| `clb.sh` | Exercise apps/clb/install.sh. |
| `compute.sh` | Exercise apps/compute's installer as the portal runs it (packaging/bazzite/install-bisect-gui.sh: one window for the bisect and the unlock). |
| `controller.sh` | Exercise apps/controller/install.sh. |
| `cores.sh` | Exercise apps/cores/install.sh. |
| `dash.sh` | Exercise dev/dash/install.sh, Nexus Dashboard's installer. |
| `datstation.sh` | Exercise apps/datstation/install.sh. |
| `demo.sh` | Exercise dev/demo/install.sh, Nexus Demo Recorder's installer. |
| `deps.sh` | Exercise dev/deps/install.sh, Nexus Deps' installer. |
| `fan.sh` | Exercise apps/fan/install.sh. |
| `itests.sh` | Exercise dev/itests/install.sh, Nexus Installer Tests's installer. |
| `not-installed.sh` | Every app's installer and the portal's, with --uninstall and with --uninstall --purge, on a computer where nothing of them is installed. |
| `nrt.sh` | Exercise dev/nrt/install.sh (and tools/nrt.sh, which forwards to it). |
| `overlay.sh` | Exercise apps/overlay/install.sh. |
| `password.sh` | Exercise apps/password/install.sh. |
| `pcsx2.sh` | Exercise apps/pcsx2/install.sh. |
| `portal.sh` | Exercise portal/install.sh. |
| `ppsspp.sh` | Exercise apps/ppsspp/install.sh. |
| `quickfix.sh` | Exercise apps/quickfix/install.sh. |
| `release-check.sh` | tools/check-release.sh. |
| `release.sh` | End to end from release tarballs. |
| `remoteplay.sh` | Exercise apps/remoteplay/install.sh. |
| `rpcs3.sh` | Exercise apps/rpcs3/install.sh. |
| `sftp.sh` | Exercise apps/sftp/install.sh. |
| `shadps4.sh` | Exercise apps/shadps4/install.sh. |
| `sounds.sh` | Exercise dev/sounds/install.sh, Nexus Sound Lab's installer. |
| `ssd.sh` | Exercise apps/ssd/install.sh. |
| `studio.sh` | Exercise dev/studio/install.sh, Nexus Remix Studio's installer. |
| `text.sh` | Exercise dev/text/install.sh, Text to Speech's installer. |
| `upscaler.sh` | Exercise apps/upscaler/install.sh. |
| `vita3k.sh` | Exercise apps/vita3k/install.sh. |
| `webcam.sh` | Exercise apps/webcam/install.sh. |
| `xenia.sh` | Exercise apps/xenia/install.sh. |

## apps/bluetooth

34 tests in 3 files, 0.4 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_boot.py` | `test_names_are_checked` | 9 |  | Names are checked. |
| `test_boot.py` | `test_install_writes_the_system_part_and_enables_what_is_chosen` |  |  | Install writes the system part and enables what is chosen. |
| `test_boot.py` | `test_install_refuses_a_bad_name_before_writing_anything` |  |  | Install refuses a bad name before writing anything. |
| `test_boot.py` | `test_uninstall_stops_and_removes_everything` |  |  | Uninstall stops and removes everything. |
| `test_boot.py` | `test_a_broken_config_is_not_installed` |  |  | A broken config is not installed. |
| `test_boot.py` | `test_what_the_app_runs_and_is_told` |  |  | What the app runs and is told. |
| `test_boot.py` | `test_main_installs_under_another_root` |  |  | Main installs under another root. |
| `test_boot.py` | `test_start_says_when_systemctl_failed` |  |  | Start says when systemctl failed. |
| `test_boot.py` | `test_devices_and_info_fields_are_read` |  |  | Devices and info fields are read. |
| `test_boot.py` | `test_listed_devices_in_pairing_mode_are_paired_and_the_search_stops` |  |  | Listed devices in pairing mode are paired and the search stops. |
| `test_boot.py` | `test_a_device_not_in_pairing_mode_is_left_alone_until_the_window_ends` |  |  | A device not in pairing mode is left alone until the window ends. |
| `test_boot.py` | `test_a_paired_device_reconnects_and_one_that_dropped_its_pairing_is_paired_again` |  |  | A paired device reconnects and one that dropped its pairing is paired again. |
| `test_boot.py` | `test_a_failed_pairing_is_tried_again` |  |  | A failed pairing is tried again. |
| `test_boot.py` | `test_one_connected_device_of_a_name_is_enough` |  |  | Every DualSense calls itself the same: once one is connected, another in pairing mode is not paired. |
| `test_boot.py` | `test_the_adapter_is_waited_for_and_switched_on` |  |  | The adapter is waited for and switched on. |
| `test_boot.py` | `test_dry_run_and_no_names_pair_nothing` |  |  | Dry run and no names pair nothing. |
| `test_boot.py` | `test_controller_battery_levels_are_read_from_the_driver` |  |  | Controller battery levels are read from the driver. |
| `test_main_window.py` | `test_version_is_the_single_source` |  |  | Version is the single source. |
| `test_main_window.py` | `test_icons_are_beside_the_package` |  |  | Icons are beside the package. |
| `test_main_window.py` | `test_window_opens_with_the_suites_header` |  | 0.1 s | Window opens with the suites header. |
| `test_main_window.py` | `test_names_are_kept_by_the_app_then_installed_with_the_search` |  |  | Names are kept by the app then installed with the search. |
| `test_main_window.py` | `test_switching_pairing_on_without_names_asks_for_them` |  |  | Switching pairing on without names asks for them. |
| `test_main_window.py` | `test_a_canceled_password_changes_nothing` |  |  | A canceled password changes nothing. |
| `test_main_window.py` | `test_batteries_alone_then_off_removes_the_system_part` |  |  | Batteries alone then off removes the system part. |
| `test_main_window.py` | `test_another_versions_system_part_offers_update` |  |  | Another versions system part offers update. |
| `test_main_window.py` | `test_bluetooth_at_login_needs_no_password` |  |  | Bluetooth at login needs no password. |
| `test_main_window.py` | `test_bluetooth_off_is_said` |  |  | Bluetooth off is said. |
| `test_main_window.py` | `test_add_dialog_checks_the_name_and_marks_listed_ones` |  |  | Add dialog checks the name and marks listed ones. |
| `test_session.py` | `test_the_adapter_and_its_switch` |  |  | The adapter and its switch. |
| `test_session.py` | `test_known_devices_paired_first_each_name_once` |  |  | Known devices paired first each name once. |
| `test_session.py` | `test_scan_searches_then_lists` |  |  | Scan searches then lists. |
| `test_session.py` | `test_the_last_search_has_its_times_and_no_host_name` |  |  | The last search has its times and no host name. |
| `test_session.py` | `test_unit_state` |  |  | Unit state. |
| `test_session.py` | `test_plasma_login_state_is_read_and_written` |  |  | Plasma login state is read and written. |

## apps/board

28 tests in 3 files, 1.8 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_log_advice.py` | `test_table_is_pairs_of_a_pattern_and_a_sentence` |  |  | Table is pairs of a pattern and a sentence. |
| `test_log_advice.py` | `test_nothing_for_no_lines` |  |  | Nothing for no lines. |
| `test_log_advice.py` | `test_real_fault_is_explained_and_counted` |  | 0.1 s | Real fault is explained and counted. |
| `test_log_advice.py` | `test_a_line_counts_for_the_first_pattern_only` |  | 0.1 s | A line counts for the first pattern only. |
| `test_log_advice.py` | `test_failed_unit_gets_its_own_commands` |  | 0.1 s | Failed unit gets its own commands. |
| `test_log_advice.py` | `test_unknown_lines_are_grouped_by_program` |  | 0.1 s | Unknown lines are grouped by program. |
| `test_smoke.py` | `test_constants_come_from_core` |  |  | Constants come from core. |
| `test_smoke.py` | `test_settings_file_unchanged` |  | 0.1 s | Settings file unchanged. |
| `test_smoke.py` | `test_main_window_builds` |  | 0.7 s | Main window builds. |
| `test_smoke.py` | `test_manual_is_the_chapter` |  |  | Manual is the chapter. |
| `test_smoke.py` | `test_manual_markdown_for_qt` |  |  | Manual markdown for qt. |
| `test_smoke.py` | `test_other_chapters_open_online` |  |  | Other chapters open online. |
| `test_smoke.py` | `test_manual_view_shows_the_chapter` |  |  | Manual view shows the chapter. |
| `test_smoke.py` | `test_results_preview_shows_image_and_emits_open_paths` |  |  | Results preview shows image and emits open paths. |
| `test_smoke.py` | `test_print_results_opens_saved_png_and_shows_preview` |  | 0.5 s | Print results opens saved png and shows preview. |
| `test_smoke.py` | `test_the_results_card_preview_copies_and_shares` |  | 0.1 s | Print results shows the card first (owner, 04-11-2026), with Save…, Copy and Share; Share is a menu (owner, 05-11-2026): each phone KDE Connect reaches, Email… and Show in file manager, the card written to the results folder first. |
| `test_steamlines.py` | `test_launch_options_reads_apps_only_and_unescapes` |  |  | Launch options reads apps only and unescapes. |
| `test_steamlines.py` | `test_old_package_line_is_stale_for_its_missing_python` |  |  | Old package line is stale for its missing python. |
| `test_steamlines.py` | `test_lines_without_gamemon_are_left_alone` |  |  | Lines without gamemon are left alone. |
| `test_steamlines.py` | `test_current_line_is_fine` |  |  | Current line is fine. |
| `test_steamlines.py` | `test_quoted_paths_with_spaces` |  |  | Quoted paths with spaces. |
| `test_steamlines.py` | `test_each_missing_part_has_its_reason` |  |  | Each missing part has its reason. |
| `test_steamlines.py` | `test_fixed_line_keeps_what_surrounds_the_gamemon_part` |  |  | Fixed line keeps what surrounds the gamemon part. |
| `test_steamlines.py` | `test_stale_lines_over_every_user_with_names_from_any_library` |  |  | Stale lines over every user with names from any library. |
| `test_steamlines.py` | `test_no_steam_or_no_name` |  |  | No steam or no name. |
| `test_steamlines.py` | `test_from_checkout` |  |  | From checkout. |
| `test_steamlines.py` | `test_ingame_page_lists_the_stale_games` |  |  | Ingame page lists the stale games. |
| `test_steamlines.py` | `test_scan_reads_only` |  |  | Scan reads only. |

## apps/cec

54 tests in 6 files, 0.7 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_bazzite.py` | `test_modes` |  |  | Modes. |
| `test_bazzite.py` | `test_cecd_is_asked_as_a_user_unit` |  |  | Cecd is asked as a user unit. |
| `test_bazzite.py` | `test_settings_follow_cecd_load_order` |  |  | Settings follow cecd load order. |
| `test_bazzite.py` | `test_written_fragment` |  |  | Written fragment. |
| `test_bazzite.py` | `test_a_broken_file_is_skipped` |  |  | A broken file is skipped. |
| `test_bazzite.py` | `test_reload_sends_hup` |  |  | Reload sends hup. |
| `test_cec.py` | `test_parse_info_of_the_ps5` |  |  | Parse info of the ps5. |
| `test_cec.py` | `test_unconfigured_and_without_display` |  |  | Unconfigured and without display. |
| `test_cec.py` | `test_devices_in_number_order` |  |  | Devices in number order. |
| `test_cec.py` | `test_topology` |  |  | Topology. |
| `test_cec.py` | `test_answers` |  |  | Answers. |
| `test_cec.py` | `test_messages` |  |  | Messages. |
| `test_cec.py` | `test_ui_command_names` |  |  | Ui command names. |
| `test_cec.py` | `test_display_name` |  |  | Display name. |
| `test_cec.py` | `test_pick_prefers_the_adapter_with_a_display` |  |  | Pick prefers the adapter with a display. |
| `test_main_window.py` | `test_shows_the_adapter_and_tv` |  | 0.1 s | Shows the adapter and tv. |
| `test_main_window.py` | `test_opening_sends_nothing_on_the_bus` |  |  | Opening sends nothing on the bus. |
| `test_main_window.py` | `test_no_adapter` |  |  | No adapter. |
| `test_main_window.py` | `test_no_display` |  |  | No display. |
| `test_main_window.py` | `test_turn_tv_on_wakes_and_switches` |  |  | Turn tv on wakes and switches. |
| `test_main_window.py` | `test_tv_that_does_not_answer` |  |  | Tv that does not answer. |
| `test_main_window.py` | `test_check_tv_and_the_receiver` |  |  | Check tv and the receiver. |
| `test_main_window.py` | `test_volume_goes_to_the_tv_without_a_receiver` |  |  | Volume goes to the tv without a receiver. |
| `test_main_window.py` | `test_unconfigured_adapter_is_configured_once` |  |  | Unconfigured adapter is configured once. |
| `test_main_window.py` | `test_topology_dialog` |  |  | Topology dialog. |
| `test_main_window.py` | `test_automatic_needs_native_mode` |  |  | Automatic needs native mode. |
| `test_main_window.py` | `test_native_mode_saves_and_reloads` |  |  | Native mode saves and reloads. |
| `test_main_window.py` | `test_use_native_runs_ujust` |  |  | Use native runs ujust. |
| `test_main_window.py` | `test_key_tester` |  |  | Key tester. |
| `test_main_window.py` | `test_standby_asks_nothing` |  |  | Standby asks nothing. |
| `test_main_window.py` | `test_tv_info` |  |  | Tv info. |
| `test_main_window.py` | `test_pause_option` |  |  | Pause option. |
| `test_main_window.py` | `test_name_without_cecd` |  |  | Name without cecd. |
| `test_main_window.py` | `test_name_with_cecd_restarts_it` |  |  | Name with cecd restarts it. |
| `test_main_window.py` | `test_remote_buttons` |  | 0.1 s | Remote buttons. |
| `test_main_window.py` | `test_remote_buttons_offers_every_button_of_cecd` |  |  | Remote buttons offers every button of cecd. |
| `test_main_window.py` | `test_two_adapters_uses_the_one_with_a_display` |  |  | Two adapters uses the one with a display. |
| `test_main_window.py` | `test_an_adapter_named_playback_gets_the_ps5s_name` |  |  | An adapter named playback gets the ps5s name. |
| `test_main_window.py` | `test_cecd_names_the_adapter_itself` |  |  | Cecd names the adapter itself. |
| `test_main_window.py` | `test_no_horizontal_scrollbar` |  |  | The window's lines fit its width, also with a larger font than KDE's default (Noto Sans 10). |
| `test_main_window.py` | `test_buttons_keep_the_desktops_look` |  |  | Plain buttons in the desktop's own gray; Turn TV on has no outline of its own. |
| `test_main_window.py` | `test_the_four_boxes_have_four_colours` |  |  | Left to right: dark blue, orange, dark blue, purple, as each box's left edge on the theme's surface. |
| `test_service.py` | `test_unit` |  |  | Unit. |
| `test_service.py` | `test_enable_and_disable` |  |  | Enable and disable. |
| `test_tvinfo.py` | `test_a_cec_1_4_tv` |  |  | A cec 1 4 tv. |
| `test_tvinfo.py` | `test_a_cec_2_0_tv_shows_what_it_reports` |  |  | A cec 2 0 tv shows what it reports. |
| `test_tvinfo.py` | `test_unknown_volume_and_flags_on_one_line` |  |  | Unknown volume and flags on one line. |
| `test_tvinfo.py` | `test_a_receiver_with_its_name_and_volume` |  |  | A receiver with its name and volume. |
| `test_watcher.py` | `test_no_answer_counts_as_off_only_after_three` |  |  | No answer counts as off only after three. |
| `test_watcher.py` | `test_on_at_start_does_nothing` |  |  | On at start does nothing. |
| `test_watcher.py` | `test_without_pause_nothing_happens` |  |  | Without pause nothing happens. |
| `test_watcher.py` | `test_pause_while_the_tv_is_off` |  |  | Pause while the tv is off. |
| `test_watcher.py` | `test_find_adapter_takes_the_one_with_a_display_and_the_users_name` |  |  | Find adapter takes the one with a display and the users name. |
| `test_watcher.py` | `test_find_adapter_renames_a_playback_adapter_unless_cecd_runs` |  |  | Find adapter renames a playback adapter unless cecd runs. |

## apps/clb

90 tests in 13 files, 2.8 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_auth.py` | `test_start_sign_in_asks_for_a_code_with_the_xbox_scope` |  |  | Start sign in asks for a code with the xbox scope. |
| `test_auth.py` | `test_wait_for_sign_in_polls_until_the_code_was_entered` |  |  | Wait for sign in polls until the code was entered. |
| `test_auth.py` | `test_wait_for_sign_in_stops_on_an_error` | 3 |  | Wait for sign in stops on an error. |
| `test_auth.py` | `test_wait_for_sign_in_ends_when_the_code_runs_out_or_is_cancelled` |  |  | Wait for sign in ends when the code runs out or is cancelled. |
| `test_auth.py` | `test_the_refresh_token_is_kept_for_the_person_only` |  |  | The refresh token is kept for the person only. |
| `test_auth.py` | `test_not_after_reads_seven_digit_fractions` |  |  | Not after reads seven digit fractions. |
| `test_auth.py` | `test_the_chain_gives_the_web_token_with_the_gamertag` |  |  | The chain gives the web token with the gamertag. |
| `test_auth.py` | `test_tokens_are_reused_until_they_run_out` |  |  | Tokens are reused until they run out. |
| `test_auth.py` | `test_home_and_cloud_tokens_with_their_default_region` |  |  | Home and cloud tokens with their default region. |
| `test_auth.py` | `test_without_game_pass_the_cloud_is_the_free_to_play_games` |  |  | Without game pass the cloud is the free to play games. |
| `test_auth.py` | `test_no_cloud_at_all_is_said` |  |  | No cloud at all is said. |
| `test_auth.py` | `test_a_refused_refresh_token_signs_out` |  |  | A refused refresh token signs out. |
| `test_auth.py` | `test_a_new_refresh_token_from_microsoft_is_kept` |  |  | A new refresh token from microsoft is kept. |
| `test_auth.py` | `test_xsts_errors_are_said_plainly` |  |  | Xsts errors are said plainly. |
| `test_auth.py` | `test_the_transfer_token_for_a_session` |  |  | The transfer token for a session. |
| `test_auth.py` | `test_signing_in_replaces_the_account` |  |  | Signing in replaces the account. |
| `test_auth.py` | `test_no_connection_is_an_http_error_with_status_zero` |  |  | No connection is an http error with status zero. |
| `test_auth.py` | `test_xbox_token_without_claims_is_an_auth_error` |  |  | Xbox token without claims is an auth error. |
| `test_channels.py` | `test_handshake_and_its_acknowledgement` |  |  | Handshake and its acknowledgement. |
| `test_channels.py` | `test_the_configuration_messages` |  |  | The configuration messages. |
| `test_channels.py` | `test_the_service_ends_the_stream` |  |  | The service ends the stream. |
| `test_channels.py` | `test_a_dialog_and_its_answer` |  |  | A dialog and its answer. |
| `test_channels.py` | `test_other_messages_are_left_alone` |  |  | Other messages are left alone. |
| `test_channels.py` | `test_control_messages` |  |  | Control messages. |
| `test_ice.py` | `test_local_candidates_of_the_first_section` |  |  | Local candidates of the first section. |
| `test_ice.py` | `test_teredo_addresses` |  |  | Teredo addresses. |
| `test_ice.py` | `test_remote_candidates_with_teredo` |  |  | Remote candidates with teredo. |
| `test_ice.py` | `test_the_answer_gets_the_candidates_once_in_every_section` |  |  | The answer gets the candidates once in every section. |
| `test_inputs.py` | `test_client_metadata_is_the_header_and_the_touch_points` |  |  | Client metadata is the header and the touch points. |
| `test_inputs.py` | `test_a_gamepad_report` |  |  | A gamepad report. |
| `test_inputs.py` | `test_axes_and_triggers_are_clamped` |  |  | Axes and triggers are clamped. |
| `test_inputs.py` | `test_metadata_and_gamepad_in_one_report` |  |  | Metadata and gamepad in one report. |
| `test_inputs.py` | `test_at_most_thirty_frames_the_newest` |  |  | At most thirty frames the newest. |
| `test_inputs.py` | `test_vibration_and_server_size_from_the_service` |  |  | Vibration and server size from the service. |
| `test_main_window.py` | `test_locale_name` |  |  | Locale name. |
| `test_main_window.py` | `test_signed_out_window` |  | 0.1 s | Signed out window. |
| `test_main_window.py` | `test_signed_in_window_lists_consoles_and_games` |  |  | Signed in window lists consoles and games. |
| `test_main_window.py` | `test_search_filters_the_games` |  |  | Search filters the games. |
| `test_main_window.py` | `test_buttons_follow_the_chosen_console` |  |  | Buttons follow the chosen console. |
| `test_main_window.py` | `test_wake` |  |  | Wake. |
| `test_main_window.py` | `test_streaming_a_console_with_remote_play_off_is_refused` |  |  | Streaming a console with remote play off is refused. |
| `test_main_window.py` | `test_streaming_opens_the_window_and_closing_it_frees_the_buttons` |  |  | Streaming opens the window and closing it frees the buttons. |
| `test_main_window.py` | `test_signing_in_with_a_code` |  |  | Signing in with a code. |
| `test_main_window.py` | `test_cancelling_the_sign_in` |  | 1.0 s | Cancelling the sign in. |
| `test_main_window.py` | `test_sign_out` |  |  | Sign out. |
| `test_main_window.py` | `test_without_cloud_gaming_the_consoles_still_show` |  |  | Without cloud gaming the consoles still show. |
| `test_main_window.py` | `test_a_refused_sign_in_signs_out` |  |  | A refused sign in signs out. |
| `test_pads.py` | `test_the_first_pad_as_the_xbox_pad` |  |  | The first pad as the xbox pad. |
| `test_pads.py` | `test_pads_connected_later_and_taken_out` |  |  | Pads connected later and taken out. |
| `test_pads.py` | `test_rumble_goes_to_the_pad` |  |  | Rumble goes to the pad. |
| `test_peer.py` | `test_codec_order_h264_main_first` |  |  | Codec order h264 main first. |
| `test_peer.py` | `test_stereo_sound` |  |  | Stereo sound. |
| `test_peer.py` | `test_a_whole_connection_with_a_stand_in_service` |  | 0.8 s | A whole connection with a stand in service. |
| `test_port.py` | `test_target_identity_and_account_path` |  |  | Target identity and account path. |
| `test_port.py` | `test_escape_leaves_stream_and_dialog_to_handle_their_keys` |  |  | Escape leaves stream and dialog to handle their keys. |
| `test_port.py` | `test_installer_private_venv_and_uninstall` |  | 0.1 s | Installer private venv and uninstall. |
| `test_privacy.py` | `test_console_ids_keep_their_last_four` |  |  | Console ids keep their last four. |
| `test_privacy.py` | `test_tokens_and_addresses_are_hidden` |  |  | Tokens and addresses are hidden. |
| `test_privacy.py` | `test_named_values_and_ordinary_text` |  |  | Named values and ordinary text. |
| `test_session.py` | `test_play_starts_a_home_session_with_the_console` |  |  | Play starts a home session with the console. |
| `test_session.py` | `test_play_starts_a_cloud_session_with_the_title` |  |  | Play starts a cloud session with the title. |
| `test_session.py` | `test_play_without_a_session_is_an_error` |  |  | Play without a session is an error. |
| `test_session.py` | `test_the_states_up_to_provisioned_with_the_queue_and_one_connect` |  |  | The states up to provisioned with the queue and one connect. |
| `test_session.py` | `test_a_failed_session_says_why` |  |  | A failed session says why. |
| `test_session.py` | `test_a_session_gone_or_cancelled_ends_the_wait` |  |  | A session gone or cancelled ends the wait. |
| `test_session.py` | `test_the_sdp_exchange_waits_for_the_answer` |  |  | The sdp exchange waits for the answer. |
| `test_session.py` | `test_an_exchange_error_is_said` |  |  | An exchange error is said. |
| `test_session.py` | `test_an_exchange_without_an_answer_gives_up` |  |  | An exchange without an answer gives up. |
| `test_session.py` | `test_the_ice_exchange` |  |  | The ice exchange. |
| `test_session.py` | `test_keepalive_and_stop` |  |  | Keepalive and stop. |
| `test_stream.py` | `test_state_texts` |  |  | State texts. |
| `test_stream.py` | `test_the_converter_keeps_only_the_newest_frame` |  | 0.1 s | The converter keeps only the newest frame. |
| `test_stream.py` | `test_a_cloud_stream_from_start_to_the_persons_end` |  | 0.2 s | A cloud stream from start to the persons end. |
| `test_stream.py` | `test_a_stream_that_cannot_start_says_why` |  |  | A stream that cannot start says why. |
| `test_stream.py` | `test_a_failed_session_is_ended_with_the_service` |  |  | A failed session is ended with the service. |
| `test_stream.py` | `test_stopping_while_the_session_starts_still_ends_it` |  |  | Stopping while the session starts still ends it. |
| `test_stream_window.py` | `test_merge_controller_and_keyboard` |  |  | Merge controller and keyboard. |
| `test_stream_window.py` | `test_the_pad_goes_to_the_stream` |  |  | The pad goes to the stream. |
| `test_stream_window.py` | `test_the_keyboard_as_a_pad` |  |  | The keyboard as a pad. |
| `test_stream_window.py` | `test_holding_view_and_menu_leaves` |  |  | Holding view and menu leaves. |
| `test_stream_window.py` | `test_ctrl_q_leaves` |  |  | Ctrl q leaves. |
| `test_stream_window.py` | `test_a_frame_drawn_is_reported` |  |  | A frame drawn is reported. |
| `test_stream_window.py` | `test_status_and_end` |  |  | Status and end. |
| `test_stream_window.py` | `test_dialogs_and_rumble` |  |  | Dialogs and rumble. |
| `test_stream_window.py` | `test_no_controller_source_leaves_the_keyboard` |  |  | No controller source leaves the keyboard. |
| `test_xbox.py` | `test_consoles_are_read_from_xbox_live` |  |  | Consoles are read from xbox live. |
| `test_xbox.py` | `test_a_console_that_is_on_needs_no_wake` |  |  | A console that is on needs no wake. |
| `test_xbox.py` | `test_wake_sends_the_power_command` |  |  | Wake sends the power command. |
| `test_xbox.py` | `test_cloud_titles_and_their_names_in_batches` |  |  | Cloud titles and their names in batches. |
| `test_xbox.py` | `test_catalogue_products_as_a_list_too` |  |  | Catalogue products as a list too. |

## apps/compute

31 tests in 5 files.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_gate.py` | `test_cu_counts_and_levels` |  |  | Cu counts and levels. |
| `test_gate.py` | `test_no_results` |  |  | No results. |
| `test_gate.py` | `test_a_fully_retested_mask_is_accepted` |  |  | A fully retested mask is accepted. |
| `test_gate.py` | `test_rejections` |  |  | Rejections. |
| `test_gate.py` | `test_uneven_mask_suggests_an_even_retest` |  |  | Uneven mask suggests an even retest. |
| `test_help_page.py` | `test_the_scripts_help_becomes_a_page` |  |  | The scripts help becomes a page. |
| `test_help_page.py` | `test_what_the_window_does_is_the_first_paragraph` |  |  | What the window does is the first paragraph. |
| `test_help_page.py` | `test_text_is_escaped_and_an_empty_help_says_so` |  |  | Text is escaped and an empty help says so. |
| `test_main_window.py` | `test_bisect_window_has_the_suite_header` |  |  | Bisect window has the suite header. |
| `test_main_window.py` | `test_start_with_the_defaults` |  |  | Start with the defaults. |
| `test_main_window.py` | `test_start_with_a_custom_baseline_and_switches` |  |  | Start with a custom baseline and switches. |
| `test_main_window.py` | `test_unattended_offers_the_autostart_service` |  |  | Unattended offers the autostart service. |
| `test_main_window.py` | `test_invalid_options_start_nothing` |  |  | Invalid options start nothing. |
| `test_main_window.py` | `test_unlock_part_without_results` |  |  | Unlock part without results. |
| `test_main_window.py` | `test_unlock_part_accepts_a_retested_mask` |  |  | Unlock part accepts a retested mask. |
| `test_main_window.py` | `test_help_opens_the_scripts_help` |  |  | Help is a pill under the title; a click opens the page. |
| `test_main_window.py` | `test_the_header_has_four_pills_in_order` |  |  | Help, Start, Show status and Reset under the title, of one width; no About (owner, 19-11-2026). |
| `test_main_window.py` | `test_the_numbers_on_one_line_and_the_switches_as_pills` |  |  | The numbers on one line and the switches as pills. |
| `test_main_window.py` | `test_one_page_with_the_unlock_under_the_bisect` |  |  | One window, one page (owner, 19-11-2026): the bisect's pills, numbers and switches, then the verdict and Install, Uninstall, Refresh and Re-check, the WGP rows, the preview with its i, and the log behind a Show logs / Hide logs button, hidden at the start. |
| `test_main_window.py` | `test_a_failed_install_shows_a_red_mark_not_a_message` |  |  | A red ! |
| `test_main_window.py` | `test_hiding_the_log_gives_its_room_back` |  |  | Show logs, then Hide logs: the window is as tall as before and the WGP rows stay together (owner, 20-11-2026: the rows spread over the log's room); a window made taller by hand keeps them together too. |
| `test_options.py` | `test_defaults_are_the_scripts_own` |  |  | Defaults are the scripts own. |
| `test_options.py` | `test_every_switch_reaches_the_command_line` |  |  | Every switch reaches the command line. |
| `test_options.py` | `test_command_is_quoted_for_bash` |  |  | Command is quoted for bash. |
| `test_options.py` | `test_validation` |  |  | Validation. |
| `test_options.py` | `test_one_round_is_allowed_for_a_control_only_retest` |  |  | One round is allowed for a control only retest. |
| `test_options.py` | `test_presets_are_valid_masks` |  |  | Presets are valid masks. |
| `test_options.py` | `test_every_baseline_choice_has_a_short_label_and_a_tooltip` |  |  | Every baseline choice has a short label and a tooltip. |
| `test_service.py` | `test_unit_resumes_the_run_with_its_settings` |  |  | Unit resumes the run with its settings. |
| `test_service.py` | `test_install_writes_and_enables_the_unit_without_starting_it` |  |  | The GUI starts the run in a terminal right after: the unit fires at the next login, not now. |
| `test_service.py` | `test_without_systemctl_the_unit_is_written_and_the_error_says_so` |  |  | Without systemctl the unit is written and the error says so. |

## apps/controller

164 tests in 13 files, 5.8 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_battery.py` | `test_modules` | 7 |  | Modules. |
| `test_battery.py` | `test_colour` | 5 |  | Colour. |
| `test_battery.py` | `test_charging_fills_the_modules_one_after_another` |  |  | Charging fills the modules one after another. |
| `test_battery.py` | `test_on_its_battery_the_level_stays` |  | 0.1 s | On its battery the level stays. |
| `test_battery.py` | `test_no_controller_is_an_empty_outline` |  |  | No controller is an empty outline. |
| `test_controller.py` | `test_feature_sizes_of_the_owners_edge` |  |  | Feature sizes of the owners edge. |
| `test_controller.py` | `test_feature_sizes_ignore_input_and_output_reports` |  |  | Feature sizes ignore input and output reports. |
| `test_controller.py` | `test_parse_info_as_hid_playstation_reads_it` |  |  | Parse info as hid playstation reads it. |
| `test_controller.py` | `test_parse_info_refuses_another_report` | 3 |  | Parse info refuses another report. |
| `test_controller.py` | `test_find_the_edge_on_usb_with_its_battery` |  |  | Find the edge on usb with its battery. |
| `test_controller.py` | `test_find_a_dualsense_over_bluetooth_and_lists_usb_first` |  |  | Find a dualsense over bluetooth and lists usb first. |
| `test_controller.py` | `test_find_skips_other_devices_and_a_missing_battery` |  |  | Find skips other devices and a missing battery. |
| `test_controller.py` | `test_find_nothing` |  |  | Find nothing. |
| `test_controller.py` | `test_holders_names_other_programs` |  |  | Holders names other programs. |
| `test_controller.py` | `test_device_pads_reports_to_the_declared_size` |  |  | Device pads reports to the declared size. |
| `test_controller.py` | `test_event_node_is_the_controllers_own_input` |  |  | Event node is the controllers own input. |
| `test_controller.py` | `test_event_node_without_input_devices` |  |  | Event node without input devices. |
| `test_controller.py` | `test_held_back_finds_a_cable_no_driver_took` |  |  | Held back finds a cable no driver took. |
| `test_controller.py` | `test_bluetooth_address_only_over_bluetooth` |  |  | Bluetooth address only over bluetooth. |
| `test_controller.py` | `test_disconnect_bluetooth` | 4 |  | Disconnect bluetooth. |
| `test_controller.py` | `test_disconnect_bluetooth_without_bluetoothctl` |  |  | Disconnect bluetooth without bluetoothctl. |
| `test_controller.py` | `test_the_player_lights_as_the_kernel_set_them` |  |  | The player lights as the kernel set them. |
| `test_controller.py` | `test_the_player_number` |  |  | The player number. |
| `test_drawing.py` | `test_paints_and_lights_parts` | 2 | 0.2 s | Paints and lights parts. |
| `test_drawing.py` | `test_the_back_buttons_only_on_the_edge` |  | 0.1 s | The back buttons only on the edge. |
| `test_drawing.py` | `test_a_pressed_button_lights_and_lets_go` |  | 0.1 s | A pressed button lights and lets go. |
| `test_drawing.py` | `test_a_pressed_face_button_takes_its_own_colour` |  | 0.1 s | A pressed face button takes its own colour. |
| `test_drawing.py` | `test_a_pulled_trigger_fills_and_a_pushed_stick_lights` |  | 0.2 s | A pulled trigger fills and a pushed stick lights. |
| `test_drawing.py` | `test_the_light_bar_shows_its_colour` |  | 0.1 s | The light bar shows its colour. |
| `test_drawing.py` | `test_an_unknown_part_is_an_error` |  |  | An unknown part is an error. |
| `test_drawing.py` | `test_the_cable_comes_down_into_the_port_and_stays_a_moment` |  |  | The cable comes down into the port and stays a moment. |
| `test_drawing.py` | `test_animations_run_only_while_needed` |  | 0.1 s | Animations run only while needed. |
| `test_drawing.py` | `test_the_dpad_is_white_with_black_borders_and_gaps` |  | 0.1 s | The dpad is white with black borders and gaps. |
| `test_drawing.py` | `test_each_part_is_named_where_it_is_drawn` | 13 |  | Each part is named where it is drawn. |
| `test_drawing.py` | `test_the_plain_dualsense_has_no_fn_or_back_buttons` |  |  | The plain dualsense has no fn or back buttons. |
| `test_drawing.py` | `test_the_tooltip_follows_the_mouse` |  |  | The tooltip follows the mouse. |
| `test_drawing.py` | `test_the_player_indicator_names_the_player` |  |  | The player indicator names the player. |
| `test_editor.py` | `test_untouched_it_gives_back_what_it_was_opened_with` |  |  | Untouched it gives back what it was opened with. |
| `test_editor.py` | `test_changes_come_back_as_settings` |  |  | Changes come back as settings. |
| `test_editor.py` | `test_a_level_it_knows_shows_and_the_back_buttons_are_no_targets` |  |  | A level it knows shows and the back buttons are no targets. |
| `test_editor.py` | `test_it_will_not_save_what_the_controller_cannot_hold` |  |  | It will not save what the controller cannot hold. |
| `test_feedback.py` | `test_the_rumble_effect_as_the_kernel_reads_it` |  |  | The rumble effect as the kernel reads it. |
| `test_feedback.py` | `test_rumble_uploads_plays_and_closes` |  |  | Rumble uploads plays and closes. |
| `test_feedback.py` | `test_the_vibration_test_runs_left_then_right` |  |  | The vibration test runs left then right. |
| `test_feedback.py` | `test_the_light_bar_over_usb` |  |  | The light bar over usb. |
| `test_feedback.py` | `test_the_light_bar_over_bluetooth_with_its_crc` |  |  | The light bar over bluetooth with its crc. |
| `test_feedback.py` | `test_parse_colour` | 5 |  | Parse colour. |
| `test_firmware.py` | `test_latest_reads_sonys_list` |  |  | Latest reads sonys list. |
| `test_firmware.py` | `test_latest_says_when_the_list_is_unusable` | 3 |  | Latest says when the list is unusable. |
| `test_firmware.py` | `test_latest_says_when_the_server_cannot_be_reached` |  |  | Latest says when the server cannot be reached. |
| `test_firmware.py` | `test_header` |  |  | Header. |
| `test_firmware.py` | `test_header_refuses_other_files` |  |  | Header refuses other files. |
| `test_firmware.py` | `test_problem_accepts_the_newer_image` |  |  | Problem accepts the newer image. |
| `test_firmware.py` | `test_problem_refuses` | 5 |  | Problem refuses. |
| `test_firmware.py` | `test_known_images_by_sha256` |  |  | Known images by sha256. |
| `test_firmware.py` | `test_download_checks_and_keeps_the_image` |  |  | Download checks and keeps the image. |
| `test_firmware.py` | `test_download_refuses_another_version` |  |  | Download refuses another version. |
| `test_firmware.py` | `test_download_says_when_it_fails` |  |  | Download says when it fails. |
| `test_firmware.py` | `test_folder_follows_xdg` |  |  | Folder follows xdg. |
| `test_idle.py` | `test_what_counts_as_use` |  |  | What counts as use. |
| `test_idle.py` | `test_a_controller_on_bluetooth_is_switched_off_after_the_minutes_unused` |  |  | A controller on bluetooth is switched off after the minutes unused. |
| `test_idle.py` | `test_on_the_cable_it_is_left_alone` |  |  | On the cable it is left alone. |
| `test_idle.py` | `test_off_reads_nothing_and_closes_what_it_read` |  |  | Off reads nothing and closes what it read. |
| `test_idle.py` | `test_a_failed_switch_off_is_logged_and_tried_again_after_another_wait` |  |  | A failed switch off is logged and tried again after another wait. |
| `test_idle.py` | `test_a_controller_that_leaves_is_let_go` |  |  | A controller that leaves is let go. |
| `test_idle.py` | `test_reports_tell_use_from_rest` |  |  | A hidraw node gives one report per read: a SEQPACKET socket pair keeps them apart as it does. |
| `test_idle.py` | `test_the_notification_goes_through_notify_send` |  |  | The notification goes through notify send. |
| `test_idle.py` | `test_several_controllers_each_have_their_own_wait_and_are_named_by_player` |  |  | Several controllers each have their own wait and are named by player. |
| `test_idle.py` | `test_without_player_lights_the_name_alone` |  |  | Without player lights the name alone. |
| `test_idle.py` | `test_the_last_used_times_go_to_the_state_file_for_the_window` |  |  | The last used times go to the state file for the window. |
| `test_idle.py` | `test_while_a_game_from_steam_runs_the_controllers_stay_on` |  |  | A game Steam started (SteamGameId in a process's environment) keeps every controller on, used or not; the wait starts over when it ends. |
| `test_idle.py` | `test_a_game_from_steam_is_known_by_its_environment` |  |  | A game from steam is known by its environment. |
| `test_idle.py` | `test_read_state_without_the_service` |  |  | Read state without the service. |
| `test_inputs.py` | `test_the_owners_edge_at_rest` |  |  | The owners edge at rest. |
| `test_inputs.py` | `test_every_button_and_the_hat` |  |  | Every button and the hat. |
| `test_inputs.py` | `test_sticks_and_triggers` |  |  | Sticks and triggers. |
| `test_inputs.py` | `test_bluetooth_has_one_byte_more_in_front` |  |  | Bluetooth has one byte more in front. |
| `test_inputs.py` | `test_other_reports_are_skipped` |  |  | Other reports are skipped. |
| `test_inputs.py` | `test_the_reader_gives_the_newest_reading` |  |  | The reader gives the newest reading. |
| `test_inputs.py` | `test_the_edges_active_profile` |  |  | Byte 49 of the USB report, as the owner's Edge sent it (23-10-2026): 0x1c on Fn + Triangle, 0x2c on Square. |
| `test_main.py` | `test_info` |  |  | Info. |
| `test_main.py` | `test_info_without_a_controller` |  |  | Info without a controller. |
| `test_main.py` | `test_info_when_the_controller_cannot_be_read` |  |  | Info when the controller cannot be read. |
| `test_main_window.py` | `test_no_controller` |  | 0.1 s | No controller. |
| `test_main_window.py` | `test_an_edge_with_an_update_waiting` |  | 0.1 s | An edge with an update waiting. |
| `test_main_window.py` | `test_no_check_at_start_when_switched_off_or_recent` |  | 0.1 s | No check at start when switched off or recent. |
| `test_main_window.py` | `test_up_to_date` |  | 0.1 s | Up to date. |
| `test_main_window.py` | `test_a_failed_check_is_shown` |  | 0.1 s | A failed check is shown. |
| `test_main_window.py` | `test_a_dualsense_over_bluetooth` |  | 0.1 s | A dualsense over bluetooth. |
| `test_main_window.py` | `test_on_bluetooth_and_up_to_date_the_cable_is_not_mentioned` |  | 0.1 s | On bluetooth and up to date the cable is not mentioned. |
| `test_main_window.py` | `test_no_access` |  | 0.1 s | No access. |
| `test_main_window.py` | `test_update_downloads_backs_up_and_sends` |  | 0.1 s | Update downloads backs up and sends. |
| `test_main_window.py` | `test_update_with_the_image_kept_names_its_check` |  | 0.1 s | Update with the image kept names its check. |
| `test_main_window.py` | `test_a_failed_update_is_shown` |  | 0.1 s | A failed update is shown. |
| `test_main_window.py` | `test_update_refused_while_steam_holds_the_controller` |  | 0.1 s | Update refused while steam holds the controller. |
| `test_main_window.py` | `test_use_a_file_refuses_one_for_another_controller` |  | 0.1 s | Use a file refuses one for another controller. |
| `test_main_window.py` | `test_use_a_file` |  | 0.1 s | Use a file. |
| `test_main_window.py` | `test_reads_again_when_the_controller_comes_back` |  | 0.1 s | Reads again when the controller comes back. |
| `test_main_window.py` | `test_two_controllers_offer_a_choice` |  | 0.1 s | Two controllers offer a choice. |
| `test_main_window.py` | `test_backup_by_hand` |  | 0.1 s | Backup by hand. |
| `test_main_window.py` | `test_the_introduction_once_after_the_first_controller` |  | 0.2 s | The introduction once after the first controller. |
| `test_main_window.py` | `test_the_introduction_of_a_dualsense_ends_with_its_battery` |  | 0.1 s | The introduction of a dualsense ends with its battery. |
| `test_main_window.py` | `test_a_controller_that_leaves_shows_connect_again` |  | 0.1 s | A controller that leaves shows connect again. |
| `test_main_window.py` | `test_the_main_page_waits_for_the_controller_after_an_update` |  | 0.1 s | The main page waits for the controller after an update. |
| `test_main_window.py` | `test_a_chosen_profile_lights_what_it_sets` |  | 0.1 s | A chosen profile lights what it sets. |
| `test_main_window.py` | `test_the_drawing_follows_the_controller_on_the_main_page` |  | 0.1 s | The drawing follows the controller on the main page. |
| `test_main_window.py` | `test_a_controller_that_leaves_while_read_stops_the_reading` |  | 0.1 s | A controller that leaves while read stops the reading. |
| `test_main_window.py` | `test_choose_a_light_bar_colour` |  | 0.1 s | Choose a light bar colour. |
| `test_main_window.py` | `test_a_light_bar_that_cannot_be_set_says_so` |  | 0.1 s | A light bar that cannot be set says so. |
| `test_main_window.py` | `test_the_vibration_test_runs_each_motor_with_the_drawing_shaking` |  | 0.2 s | The vibration test runs each motor with the drawing shaking. |
| `test_main_window.py` | `test_the_update_shows_data_flowing` |  | 0.4 s | The update shows data flowing. |
| `test_main_window.py` | `test_on_bluetooth_with_the_cable_in_offers_the_cable` |  | 0.1 s | On bluetooth with the cable in offers the cable. |
| `test_main_window.py` | `test_use_the_cable_that_fails_says_what_to_do` |  | 0.1 s | Use the cable that fails says what to do. |
| `test_main_window.py` | `test_the_boxes_keep_their_width_from_usb_to_bluetooth` |  | 0.1 s | The boxes keep their width from usb to bluetooth. |
| `test_main_window.py` | `test_every_button_says_what_it_does` |  | 0.1 s | Every button says what it does. |
| `test_main_window.py` | `test_the_firmware_box_shows_the_kept_files_sha256_check` |  | 0.1 s | The firmware box shows the kept files sha256 check. |
| `test_main_window.py` | `test_a_known_file_is_named_as_such` |  | 0.1 s | A known file is named as such. |
| `test_main_window.py` | `test_the_profile_cards_and_colours_say_their_own_thing` |  | 0.1 s | The profile cards and colours say their own thing. |
| `test_main_window.py` | `test_the_info_sheet_shows_what_the_controller_reports` |  | 0.1 s | The info sheet shows what the controller reports. |
| `test_main_window.py` | `test_turn_off_only_over_bluetooth` |  | 0.1 s | Turn off only over bluetooth. |
| `test_main_window.py` | `test_the_top_boxes_share_the_width_and_the_colours_follow_the_drawing` |  | 0.1 s | The top boxes share the width and the colours follow the drawing. |
| `test_main_window.py` | `test_the_cards_offer_create_edit_and_clear_but_not_on_the_default` |  | 0.1 s | The cards offer create edit and clear but not on the default. |
| `test_main_window.py` | `test_over_bluetooth_the_profiles_cannot_be_changed` |  | 0.1 s | Over bluetooth the profiles cannot be changed. |
| `test_main_window.py` | `test_create_starts_from_the_default_backs_up_and_writes` |  |  | Create starts from the default backs up and writes. |
| `test_main_window.py` | `test_edit_keeps_the_profiles_own_bytes` |  |  | Edit keeps the profiles own bytes. |
| `test_main_window.py` | `test_a_cancelled_editor_writes_nothing` |  |  | A cancelled editor writes nothing. |
| `test_main_window.py` | `test_clear_asks_backs_up_and_empties` |  |  | Clear asks backs up and empties. |
| `test_main_window.py` | `test_a_write_the_controller_refuses_says_so_with_the_backup` |  | 0.1 s | A write the controller refuses says so with the backup. |
| `test_main_window.py` | `test_the_active_profile_is_marked_and_follows_fn` |  | 0.1 s | The active profile is marked and follows fn. |
| `test_main_window.py` | `test_the_drawing_shows_the_player_lights` |  | 0.1 s | The drawing shows the player lights. |
| `test_main_window.py` | `test_the_idle_choice_is_saved_for_the_service` |  | 0.1 s | The idle choice is saved for the service. |
| `test_main_window.py` | `test_the_live_pills_in_the_header` |  | 0.1 s | The live pills in the header. |
| `test_main_window.py` | `test_on_the_cable_the_off_pill_says_cable` |  | 0.1 s | On the cable the off pill says cable. |
| `test_profiles.py` | `test_the_owners_default_profile` |  |  | The owners default profile. |
| `test_profiles.py` | `test_an_empty_slot` |  |  | An empty slot. |
| `test_profiles.py` | `test_a_profile_with_curves_triggers_and_remapped_buttons` |  |  | A profile with curves triggers and remapped buttons. |
| `test_profiles.py` | `test_a_changed_byte_fails_the_checksum` |  |  | A changed byte fails the checksum. |
| `test_profiles.py` | `test_read_asks_for_the_twelve_reports_in_order` |  |  | Read asks for the twelve reports in order. |
| `test_profiles.py` | `test_backup_keeps_the_reports` |  |  | Backup keeps the reports. |
| `test_profiles.py` | `test_backup_path` |  |  | Backup path. |
| `test_profiles.py` | `test_changed_parts` |  |  | Changed parts. |
| `test_profiles.py` | `test_settings_of_the_default_profile_keep_its_curve_points` |  |  | Settings of the default profile keep its curve points. |
| `test_profiles.py` | `test_the_owners_write_test_as_built_by_the_app` |  |  | The reports the owner's Edge took on 23-10-2026: the default profile renamed "Write test" in Fn + Square, with the per-report CRCs the test script printed. |
| `test_profiles.py` | `test_build_puts_every_setting_in_and_keeps_the_rest` |  |  | Build puts every setting in and keeps the rest. |
| `test_profiles.py` | `test_curve_points_follow_the_tables` |  |  | Curve points follow the tables. |
| `test_profiles.py` | `test_build_refuses_what_the_controller_cannot_hold` |  |  | Build refuses what the controller cannot hold. |
| `test_profiles.py` | `test_write_reads_back_and_clear_empties` |  |  | Write reads back and clear empties. |
| `test_profiles.py` | `test_the_default_profile_is_never_written_or_cleared` |  |  | The default profile is never written or cleared. |
| `test_profiles.py` | `test_a_write_the_controller_does_not_keep_is_an_error` |  |  | A write the controller does not keep is an error. |
| `test_specs.py` | `test_every_fact_has_an_official_source` |  |  | Every fact has an official source. |
| `test_specs.py` | `test_the_edges_facts_as_sony_gives_them` |  |  | The edges facts as sony gives them. |
| `test_specs.py` | `test_no_facts_for_the_plain_dualsense_without_a_source` |  |  | No facts for the plain dualsense without a source. |
| `test_specs.py` | `test_the_parts_out_of_the_drawing` |  |  | The parts out of the drawing. |
| `test_specs.py` | `test_the_sheet_numbers_its_sources` |  |  | The sheet numbers its sources. |
| `test_specs.py` | `test_the_sheet_of_a_model_without_facts_says_so` |  |  | The sheet of a model without facts says so. |
| `test_updater.py` | `test_sends_header_image_verify_and_finalize_in_57_byte_pieces` |  |  | Sends header image verify and finalize in 57 byte pieces. |
| `test_updater.py` | `test_waits_while_busy_and_asks_again` |  |  | Waits while busy and asks again. |
| `test_updater.py` | `test_a_start_answered_with_retry_goes_on_as_dualsense_updater_rs_does` |  |  | A start answered with retry goes on as dualsense updater rs does. |
| `test_updater.py` | `test_stops_at_an_error_and_never_finalizes` | 6 |  | Stops at an error and never finalizes. |
| `test_updater.py` | `test_stops_when_the_controller_stays_busy` |  |  | Stops when the controller stays busy. |
| `test_updater.py` | `test_a_status_for_another_step_is_an_error` |  |  | A status for another step is an error. |
| `test_updater.py` | `test_a_controller_that_leaves_is_an_error` |  |  | A controller that leaves is an error. |
| `test_updater.py` | `test_a_controller_that_restarts_at_finalize_is_fine` |  |  | A controller that restarts at finalize is fine. |
| `test_updater.py` | `test_refuses_an_image_shorter_than_its_header` |  |  | Refuses an image shorter than its header. |

## apps/cores

29 tests in 4 files.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_gate.py` | `test_verdicts` |  |  | Verdicts. |
| `test_gate.py` | `test_no_results` |  |  | No results. |
| `test_gate.py` | `test_a_finished_clean_bisect_is_accepted` |  |  | A finished clean bisect is accepted. |
| `test_gate.py` | `test_rejections` |  |  | Rejections. |
| `test_gate.py` | `test_a_failing_core_rejects_the_whole_unlock` |  |  | A failing core rejects the whole unlock. |
| `test_gate.py` | `test_aborted_attempts_do_not_count` |  |  | Aborted attempts do not count. |
| `test_gate.py` | `test_notes_do_not_block` |  |  | Notes do not block. |
| `test_help_page.py` | `test_the_scripts_help_becomes_a_page` |  |  | The scripts help becomes a page. |
| `test_help_page.py` | `test_a_sentence_above_a_list_of_terms_is_its_paragraph` |  |  | 'For a longer, harsher burn-in ...' then --load and --rasdaemon: a paragraph and a table, not one run-on line. |
| `test_help_page.py` | `test_what_the_window_does_is_the_first_paragraph` |  |  | What the window does is the first paragraph. |
| `test_help_page.py` | `test_text_is_escaped_and_an_empty_help_says_so` |  |  | Text is escaped and an empty help says so. |
| `test_main_window.py` | `test_the_window_has_the_suite_header` |  |  | The window has the suite header. |
| `test_main_window.py` | `test_start_with_the_defaults` |  |  | Start with the defaults. |
| `test_main_window.py` | `test_start_with_mprime_and_rasdaemon` |  |  | Start with mprime and rasdaemon. |
| `test_main_window.py` | `test_unattended_installs_the_resume_unit` |  |  | Unattended installs the resume unit. |
| `test_main_window.py` | `test_the_estimate_is_short_and_follows_the_options` |  |  | The estimate is short and follows the options. |
| `test_main_window.py` | `test_help_opens_the_scripts_help` |  |  | Help is a pill under the title; a click opens the page. |
| `test_main_window.py` | `test_the_header_has_four_pills_in_order` |  |  | Help, Start, Show status and Reset under the title, of one width; no About (owner, 20-11-2026). |
| `test_main_window.py` | `test_the_numbers_on_one_line_and_the_switches_as_pills` |  |  | The numbers on one line and the switches as pills. |
| `test_main_window.py` | `test_unlock_part_without_results` |  |  | Unlock part without results. |
| `test_main_window.py` | `test_one_page_with_the_unlock_under_the_bisect` |  |  | One window, one page (owner, 20-11-2026, as CU Tools): the bisect's pills, numbers and switches, then the verdict and Install, Uninstall, Refresh, Root status and Re-check, the 8 cores with their i, and the log behind a Show logs / Hide logs button, hidden at the start. |
| `test_main_window.py` | `test_a_failed_install_shows_a_red_mark_not_a_message` |  |  | A red ! |
| `test_main_window.py` | `test_hiding_the_log_gives_its_room_back` |  |  | Show logs, then Hide logs: the window is as tall as before and the cores stay where they were (owner, 20-11-2026: CU Tools' rows spread over the log's room); a window made taller by hand keeps them in place too. |
| `test_options_and_service.py` | `test_defaults_are_the_scripts_own` |  |  | Defaults are the scripts own. |
| `test_options_and_service.py` | `test_every_switch_reaches_the_command_line` |  |  | Every switch reaches the command line. |
| `test_options_and_service.py` | `test_validation` |  |  | Validation. |
| `test_options_and_service.py` | `test_load_tools` |  |  | Load tools. |
| `test_options_and_service.py` | `test_unit_resumes_with_the_gui_settings_and_always_auto` |  |  | Unit resumes with the gui settings and always auto. |
| `test_options_and_service.py` | `test_install_enables_the_unit_without_starting_it` |  |  | enable, not enable --now: the GUI starts the run itself, a second instance would share its state. |

## apps/datstation

39 tests in 7 files, 2.1 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_content.py` | `test_the_history_html_and_links` |  |  | The history html and links. |
| `test_content.py` | `test_no_console_pictures_ship` |  |  | No console pictures ship. |
| `test_content.py` | `test_the_region_tables_are_square` |  |  | The region tables are square. |
| `test_main_window.py` | `test_the_tiles_open_their_pages_and_back_returns` |  | 0.1 s | The tiles open their pages and back returns. |
| `test_main_window.py` | `test_arrow_keys_move_between_tiles` |  |  | Arrow keys move between tiles. |
| `test_main_window.py` | `test_four_by_four_with_coming_soon_in_the_empty_slots` |  |  | Four by four with coming soon in the empty slots. |
| `test_main_window.py` | `test_the_menu_looks_like_back_and_the_state_stands_on_the_titles_baseline` |  |  | The menu looks like back and the state stands on the titles baseline. |
| `test_main_window.py` | `test_the_steam_state_and_adding_to_steam` |  | 0.4 s | The steam state and adding to steam. |
| `test_main_window.py` | `test_adding_is_refused_in_game_mode` |  |  | Adding is refused in game mode. |
| `test_main_window.py` | `test_the_quiz_page_plays_a_round` |  |  | The quiz page plays a round. |
| `test_main_window.py` | `test_a_perfect_quick_quiz_and_the_mute_setting` |  |  | A perfect quick quiz and the mute setting. |
| `test_main_window.py` | `test_the_scores_page_shows_the_store` |  | 0.1 s | The scores page shows the store. |
| `test_main_window.py` | `test_the_news_page_with_a_test_feed` |  | 0.1 s | The news page with a test feed. |
| `test_main_window.py` | `test_the_history_page_links` |  |  | The history page links. |
| `test_main_window.py` | `test_the_versions_page_switches_systems` |  | 0.1 s | The versions page switches systems. |
| `test_main_window.py` | `test_the_quiz_tile_counts_the_shipped_questions` |  |  | The quiz tile counts the shipped questions. |
| `test_news.py` | `test_the_feed_parses` |  |  | The feed parses. |
| `test_news.py` | `test_cleaning_and_dates` |  |  | Cleaning and dates. |
| `test_news.py` | `test_only_playstation_links_are_allowed` | 9 |  | Only playstation links are allowed. |
| `test_news.py` | `test_errors_are_sentences` |  |  | Errors are sentences. |
| `test_news.py` | `test_the_page_html` |  |  | The page html. |
| `test_quiz.py` | `test_the_shipped_questions_are_complete_and_answerable` |  |  | The shipped questions are complete and answerable. |
| `test_quiz.py` | `test_matching_categories` |  |  | Matching categories. |
| `test_quiz.py` | `test_a_round_scores_and_keeps_time` |  |  | A round scores and keeps time. |
| `test_quiz.py` | `test_skip_pause_and_running_out_of_time` |  |  | Skip pause and running out of time. |
| `test_quiz.py` | `test_a_category_runs_out_of_questions` |  |  | A category runs out of questions. |
| `test_quiz.py` | `test_a_perfect_round_then_the_next_and_the_results` |  |  | A perfect round then the next and the results. |
| `test_quiz.py` | `test_the_quick_quiz_is_short_and_not_saved` |  |  | The quick quiz is short and not saved. |
| `test_quiz.py` | `test_the_review_by_percentage` | 8 |  | The review by percentage. |
| `test_scores.py` | `test_rounds_add_scores_and_perfect_rounds_trophies` |  |  | Rounds add scores and perfect rounds trophies. |
| `test_scores.py` | `test_a_damaged_or_missing_file_is_an_empty_store` |  |  | A damaged or missing file is an empty store. |
| `test_scores.py` | `test_the_default_path_is_under_the_data_home` |  |  | The default path is under the data home. |
| `test_steam_shortcut.py` | `test_the_entry_and_recognising_it` |  |  | The entry and recognising it. |
| `test_steam_shortcut.py` | `test_add_update_and_remove_for_every_user` |  | 0.6 s | Add update and remove for every user. |
| `test_steam_shortcut.py` | `test_the_artwork_has_steams_sizes` |  | 0.3 s | The artwork has steams sizes. |
| `test_steam_shortcut.py` | `test_refusals` |  |  | Refusals. |
| `test_versions.py` | `test_every_shipped_file_loads` |  |  | Every shipped file loads. |
| `test_versions.py` | `test_the_three_shapes_and_bad_files` |  |  | The three shapes and bad files. |
| `test_versions.py` | `test_the_html_of_an_entry` |  |  | The html of an entry. |

## apps/fan

37 tests in 2 files, 0.4 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_guard.py` | `test_reads_the_ps5` |  |  | Reads the ps5. |
| `test_guard.py` | `test_gpu_on_kernel_731` |  |  | Gpu on kernel 731. |
| `test_guard.py` | `test_hwmon_numbers_do_not_matter` |  |  | Hwmon numbers do not matter. |
| `test_guard.py` | `test_a_broken_reading_is_no_temperature` |  |  | A broken reading is no temperature. |
| `test_guard.py` | `test_no_fan_driver` |  |  | No fan driver. |
| `test_guard.py` | `test_mode_text` | 3 |  | Mode text. |
| `test_guard.py` | `test_limits_problem` | 7 |  | Limits problem. |
| `test_guard.py` | `test_defaults_follow_the_kernel` |  |  | Defaults follow the kernel. |
| `test_guard.py` | `test_cool_ps5_does_nothing` |  |  | Cool ps5 does nothing. |
| `test_guard.py` | `test_warns_once_and_rearms_5_below` |  |  | Warns once and rearms 5 below. |
| `test_guard.py` | `test_cooling_turns_the_fan_full_and_the_boost_off_then_puts_the_fan_back` |  |  | Cooling turns the fan full and the boost off then puts the fan back. |
| `test_guard.py` | `test_without_ps5_control_only_the_fan` |  |  | Without ps5 control only the fan. |
| `test_guard.py` | `test_a_manual_duty_is_put_back` |  |  | A manual duty is put back. |
| `test_guard.py` | `test_shutdown_after_the_hold` |  |  | Shutdown after the hold. |
| `test_guard.py` | `test_no_shutdown_when_it_cools_in_time` |  |  | No shutdown when it cools in time. |
| `test_guard.py` | `test_a_broken_sensor_never_shuts_down` |  |  | A broken sensor never shuts down. |
| `test_guard.py` | `test_one_sensor_is_enough` |  |  | One sensor is enough. |
| `test_guard.py` | `test_state_file` |  |  | State file. |
| `test_guard.py` | `test_desktop_notification_per_user` |  |  | Desktop notification per user. |
| `test_guard.py` | `test_install_and_uninstall` |  |  | Install and uninstall. |
| `test_guard.py` | `test_install_refuses_bad_limits` |  |  | Install refuses bad limits. |
| `test_guard.py` | `test_install_says_when_the_service_does_not_start` |  |  | Install says when the service does not start. |
| `test_guard.py` | `test_broken_config_means_defaults` |  |  | Broken config means defaults. |
| `test_guard.py` | `test_outdated` |  |  | Outdated. |
| `test_guard.py` | `test_main_install_prints_an_answer` |  |  | Main install prints an answer. |
| `test_guard.py` | `test_command_and_answer` |  |  | Command and answer. |
| `test_main_window.py` | `test_shows_the_ps5` |  | 0.1 s | Shows the ps5. |
| `test_main_window.py` | `test_gpu_on_kernel_731` |  |  | Gpu on kernel 731. |
| `test_main_window.py` | `test_no_fan_driver` |  |  | No fan driver. |
| `test_main_window.py` | `test_turn_on_installs_with_the_limits` |  |  | Turn on installs with the limits. |
| `test_main_window.py` | `test_bad_limits_block_apply` |  |  | Bad limits block apply. |
| `test_main_window.py` | `test_running_guard_and_its_events` |  |  | Running guard and its events. |
| `test_main_window.py` | `test_stale_state_is_not_running` |  |  | Stale state is not running. |
| `test_main_window.py` | `test_outdated_guard` |  |  | Outdated guard. |
| `test_main_window.py` | `test_turn_off` |  |  | Turn off. |
| `test_main_window.py` | `test_helper_error_is_shown` |  |  | Helper error is shown. |
| `test_main_window.py` | `test_no_question_no_change` |  |  | No question no change. |

## apps/overlay

18 tests in 2 files, 0.2 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_overlay.py` | `test_format_reading` |  |  | Format reading. |
| `test_overlay.py` | `test_format_missing_values` |  |  | Format missing values. |
| `test_overlay.py` | `test_warm_is_orange` |  |  | Warm is orange. |
| `test_overlay.py` | `test_window_shows_the_ps5` |  |  | Window shows the ps5. |
| `test_overlay.py` | `test_kernel_without_gpu_sensors` |  |  | Kernel without gpu sensors. |
| `test_overlay.py` | `test_window_flags` |  |  | Window flags. |
| `test_overlay.py` | `test_rows_can_be_hidden` |  |  | Rows can be hidden. |
| `test_overlay.py` | `test_the_last_row_stays` |  |  | The last row stays. |
| `test_overlay.py` | `test_menu_choices_are_remembered` |  |  | Menu choices are remembered. |
| `test_overlay.py` | `test_position_is_remembered` |  |  | Position is remembered. |
| `test_sensors.py` | `test_values_from_a_ps5` |  |  | Values from a ps5. |
| `test_sensors.py` | `test_kernel_without_gpu_sensors` |  |  | Kernel without gpu sensors. |
| `test_sensors.py` | `test_cpufreq_wins_when_present` |  |  | Cpufreq wins when present. |
| `test_sensors.py` | `test_fan_modes` |  |  | Fan modes. |
| `test_sensors.py` | `test_cpu_load_over_two_readings` |  |  | Cpu load over two readings. |
| `test_sensors.py` | `test_rates_over_two_readings` |  |  | Rates over two readings. |
| `test_sensors.py` | `test_nothing_there` |  |  | Nothing there. |
| `test_sensors.py` | `test_without_ps5_fan` |  |  | Without ps5 fan. |

## apps/password

22 tests in 2 files, 0.4 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_generator.py` | `test_the_rules_are_eight_or_fifteen_characters_of_printable_ascii_without_the_space` |  |  | The rules are eight or fifteen characters of printable ascii without the space. |
| `test_generator.py` | `test_every_password_has_a_capital_a_small_letter_a_number_and_a_special_character` | 2 | 0.1 s | Every password has a capital a small letter a number and a special character. |
| `test_generator.py` | `test_meets_rules_refuses_what_lacks_a_kind_a_length_or_a_character` |  |  | Meets rules refuses what lacks a kind a length or a character. |
| `test_generator.py` | `test_a_password_has_no_other_length` |  |  | A password has no other length. |
| `test_generator.py` | `test_the_characters_come_from_secrets` |  |  | The characters come from secrets. |
| `test_generator.py` | `test_every_kind_turns_up_in_every_position` |  | 0.1 s | Every kind turns up in every position. |
| `test_generator.py` | `test_a_generator_never_gives_the_same_password_twice` |  |  | A generator never gives the same password twice. |
| `test_generator.py` | `test_a_generator_remembers_digests_not_passwords` |  |  | A generator remembers digests not passwords. |
| `test_main_window.py` | `test_version_is_the_single_source` |  |  | Version is the single source. |
| `test_main_window.py` | `test_icons_are_beside_the_package` |  |  | Icons are beside the package. |
| `test_main_window.py` | `test_window_opens_with_the_suites_header_and_a_password` |  | 0.1 s | Window opens with the suites header and a password. |
| `test_main_window.py` | `test_the_password_is_shown_as_plain_text` |  |  | A password with angle brackets is shown as it is, not read as markup. |
| `test_main_window.py` | `test_each_pill_makes_a_new_password_of_its_length` | 2 |  | Each pill makes a new password of its length. |
| `test_main_window.py` | `test_the_window_names_the_standards_with_both_lengths` |  |  | The window names the standards with both lengths. |
| `test_main_window.py` | `test_a_long_password_fits_the_window` |  |  | A long password fits the window. |
| `test_main_window.py` | `test_copy_puts_the_password_on_the_clipboard_as_a_secret` |  |  | Copy puts the password on the clipboard as a secret. |
| `test_main_window.py` | `test_the_clipboard_is_cleared_when_the_time_is_over` |  |  | The clipboard is cleared when the time is over. |
| `test_main_window.py` | `test_a_new_password_takes_the_old_one_off_the_clipboard` |  |  | A new password takes the old one off the clipboard. |
| `test_main_window.py` | `test_what_you_copied_elsewhere_stays_on_the_clipboard` |  |  | What you copied elsewhere stays on the clipboard. |
| `test_main_window.py` | `test_closing_ends_the_password` |  |  | Closing ends the password. |
| `test_main_window.py` | `test_nothing_is_written` |  |  | The folder the settings would go to stays empty. |
| `test_main_window.py` | `test_the_package_opens_no_file_and_keeps_no_setting` |  |  | The package opens no file and keeps no setting. |

## apps/pcsx2

141 tests in 14 files, 19.0 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_catalogue.py` | `test_titles_from_the_game_index` |  |  | Titles from the game index. |
| `test_catalogue.py` | `test_the_titles_are_read_again_when_the_file_changes` |  |  | The titles are read again when the file changes. |
| `test_catalogue.py` | `test_widescreen_patches_are_looked_up_as_pcsx2_does` |  |  | Widescreen patches are looked up as pcsx2 does. |
| `test_catalogue.py` | `test_the_files_are_taken_out_of_the_appimage` |  |  | --appimage-extract with each file's path inside, in a work folder beside the AppImage; the files land beside it and the work folder goes. |
| `test_catalogue.py` | `test_a_failed_extraction_leaves_nothing_behind` |  |  | A failed extraction leaves nothing behind. |
| `test_controllers.py` | `test_the_controllers_connected` |  |  | The controllers connected. |
| `test_emulator.py` | `test_the_pin_points_at_the_release` |  |  | The pin points at the release. |
| `test_emulator.py` | `test_install_and_remove` |  |  | Install and remove. |
| `test_emulator.py` | `test_install_takes_pcsx2s_catalogue_out` |  |  | PCSX2's titles and patches come out of the AppImage beside it; without them the install stands all the same. |
| `test_emulator.py` | `test_an_older_version_is_replaced` |  |  | An older version is replaced. |
| `test_emulator.py` | `test_pcsx2_updated_itself` |  |  | PCSX2's own update writes another build over the AppImage it runs from, in the same folder. |
| `test_emulator.py` | `test_a_different_file_is_refused` |  |  | A different file is refused. |
| `test_emulator.py` | `test_a_failed_install_keeps_the_installed_one` |  |  | A failed install keeps the installed one. |
| `test_emulator.py` | `test_download_errors_say_what_happened` |  |  | Download errors say what happened. |
| `test_emulator.py` | `test_a_newer_pcsx2_stable` |  |  | A newer pcsx2 stable. |
| `test_games.py` | `test_system_cnf_is_read` |  |  | System cnf is read. |
| `test_games.py` | `test_the_serial_as_pcsx2_shows_it` |  |  | The serial as pcsx2 shows it. |
| `test_games.py` | `test_an_iso_is_read` |  |  | An iso is read. |
| `test_games.py` | `test_files_that_are_no_ps2_games` |  |  | Files that are no ps2 games. |
| `test_games.py` | `test_compressed_images_are_listed_under_their_name` |  |  | Compressed images are listed under their name. |
| `test_games.py` | `test_scan_finds_games_sorted_once_and_not_too_deep` |  |  | Scan finds games sorted once and not too deep. |
| `test_games.py` | `test_the_crc_as_pcsx2_computes_it` |  |  | Every 32-bit word XORed; the bytes after the last whole word left out. |
| `test_games.py` | `test_the_title_from_pcsx2s_catalogue_or_the_file` |  |  | The title from pcsx2s catalogue or the file. |
| `test_games.py` | `test_a_serial_is_cut_out_of_a_files_name` |  |  | A serial is cut out of a files name. |
| `test_games.py` | `test_a_failing_card_ends_no_scan` |  |  | A failing card ends no scan. |
| `test_library.py` | `test_fixed_folders_are_made_and_found` |  |  | Fixed folders are made and found. |
| `test_library.py` | `test_removal_items_are_the_image_and_the_shortcut` |  |  | Removal items are the image and the shortcut. |
| `test_main_window.py` | `test_before_installing` |  | 0.1 s | Before installing. |
| `test_main_window.py` | `test_installed_with_bios_and_games` |  | 0.1 s | Installed with bios and games. |
| `test_main_window.py` | `test_the_controller_state` |  |  | Beside the title: whether a controller is connected, from the kernel's list, looked at again every few seconds (owner, 24-10-2026: a controller switched off by its idle timer left a game without one). |
| `test_main_window.py` | `test_the_play_time_in_the_header` |  | 0.1 s | The time spent in all games together, as PCSX2 counts it in playtime.dat, with each game in the tip; a dash while there is none. |
| `test_main_window.py` | `test_pcsx2_updated_itself` |  | 0.1 s | Pcsx2 updated itself. |
| `test_main_window.py` | `test_the_bios_is_taken_from_the_apps_folder` |  | 0.2 s | The dump put in Games/PS2/BIOS is copied into PCSX2's bios folder with the files beside it, once PCSX2 is installed and while it does not run (owner, 03-11-2026), and PCSX2 uses it; an unchanged folder copies nothing again. |
| `test_main_window.py` | `test_pcsx2_is_set_up_once_installed` |  | 0.1 s | Before PCSX2 is installed nothing is written; then its settings get what the app owns, and a game starts straight away. |
| `test_main_window.py` | `test_pcsx2s_titles_name_the_games` |  | 0.1 s | With PCSX2's catalog beside the AppImage, a game is named as PCSX2 names it, in the table and in Steam; a game PCSX2 does not know keeps its file's name, without the serial in it. |
| `test_main_window.py` | `test_each_games_screen` |  | 0.1 s | The Screen column: Widescreen only for a game PCSX2 has a widescreen patch for, the choice kept in the game's own settings in PCSX2; a compressed image has no choice; nothing is written while PCSX2 runs. |
| `test_main_window.py` | `test_the_apps_own_game_folders` |  | 0.1 s | The games are put in Games/PS2 in the home folder, made with its BIOS folder when the app opens, and in Games/PS2 on a removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); no folder is chosen or remembered any more. |
| `test_main_window.py` | `test_a_compressed_image_is_marked` |  | 0.1 s | A compressed image is marked. |
| `test_main_window.py` | `test_install_runs_off_the_window` |  | 0.2 s | Install runs off the window. |
| `test_main_window.py` | `test_steam_added_and_taken_out` |  | 0.5 s | Steam added and taken out. |
| `test_main_window.py` | `test_update_steam_reads_the_file_back` |  | 0.5 s | Right after the write, while Steam is closed, Steam's file is read back (owner, 03-11-2026): a game written but not found is named on the status line, and a file that cannot be read back is said. |
| `test_main_window.py` | `test_a_shortcut_named_before_the_system_prefix_is_renamed` |  | 0.4 s | A shortcut named by the title alone, as before "[PS2] ": Update Steam is on for it and renames it, with its play time; the artwork under its old number goes. |
| `test_main_window.py` | `test_a_shortcut_of_a_game_no_longer_found_is_taken_out` |  | 0.1 s | A shortcut of a game no longer found is taken out. |
| `test_main_window.py` | `test_no_steam_game_mode_or_no_wrapper` |  | 0.2 s | No steam game mode or no wrapper. |
| `test_main_window.py` | `test_the_blue_look` |  | 0.1 s | The blue look. |
| `test_main_window.py` | `test_a_newer_pcsx2_is_mentioned` |  | 0.1 s | A newer pcsx2 is mentioned. |
| `test_main_window.py` | `test_the_log_tab` |  | 0.1 s | What the window says goes to the Log tab with the time, after what the log file held already; the Settings and Memory cards tabs write there too. |
| `test_main_window.py` | `test_clear_logs_empties_the_log` |  |  | Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones beside it removed and the Log tab emptied with them, the open page kept. |
| `test_main_window.py` | `test_the_blueprint_layout` |  |  | The managers' design (owner, 18-11-2026, PPSSPP Manager's): the window 900 wide when it opens, which is also its narrowest, and what is in it asks for no more; Play time the last pill of the second row; the six tabs share the whole width, the last one up to the margin, with no line over them; under the header's pills the two links alone, in the type of a pill's caption, each still a link. |
| `test_main_window.py` | `test_the_steam_link` |  |  | The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the boxes, Screen setting and Start game do, and Steam in it is a link the app opens itself. |
| `test_main_window.py` | `test_pcsx2s_window` |  |  | PCSX2 settings, left of Remove game… (owner, 18-11-2026, as PPSSPP Manager's): PCSX2's own window, through the run wrapper and without a game; off until PCSX2 is installed. |
| `test_main_window.py` | `test_pcsx2s_last_run_is_logged_once` |  | 0.2 s | PCSX2's own log of its last run (the game, the play time, the controller) goes into the app's log the next time the window looks, once per run; a run without a game is nothing to say. |
| `test_main_window.py` | `test_the_tabs_follow_pcsx2s_folder` |  | 0.2 s | The Settings and Memory cards tabs read PCSX2's folder when the window refreshes, and nothing of theirs is written while PCSX2 runs. |
| `test_main_window.py` | `test_covers_with_the_suites_key` |  | 1.0 s | Steam artwork… keeps the suite's key; Update Steam then looks up the games and puts all four pictures in place of the drawn ones, and a game in Steam not looked up yet makes the button do something again. |
| `test_main_window.py` | `test_bazzites_volume_for_pcsx2` |  | 0.1 s | The volume Bazzite remembers for PCSX2 (WirePlumber's stream-properties, core's sound): in the Settings tab's Sound box, and said once while PCSX2 is muted there (owner, 24-10-2026, as RPCS3 Manager's). |
| `test_main_window.py` | `test_the_tabs_are_not_squeezed_under_the_introduction` |  | 0.1 s | The introduction's lines count in the window's minimum height (core's WrappedLabel; owner, 24-10-2026, from RPCS3 Manager), so the tabs below get their minimum. |
| `test_main_window.py` | `test_the_state_lines_links_take_a_click` |  |  | The PCSX2 and BIOS lines hold links (the release notes, PCSX2's BIOS page): a state line takes a click on a link, not only a selection of its text (owner, 24-10-2026: found in shadPS4 Manager's window, built the same way, where a click on a link did nothing). |
| `test_main_window.py` | `test_unmute_bazzites_volume` |  | 0.2 s | Unmute beside Bazzite's volume (owner, 24-10-2026): shown while PCSX2 is muted there only; a click runs core's unmute off the window and the row follows what WirePlumber stored; a failure is said in red. |
| `test_main_window.py` | `test_remove_game_asks_what_to_keep` |  | 0.2 s | Remove game… (owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked deletes the rows still ticked off the window's thread and says what went and what stayed. |
| `test_main_window.py` | `test_start_game_starts_the_chosen_game_through_steam` |  | 0.4 s | The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your games through Steam, by its shortcut's number, and the open tab stays open. |
| `test_memcard_icon.py` | `test_rez_as_mymcs_opengl_viewer_draws_it` |  | 0.8 s | Rez as mymcs opengl viewer draws it. |
| `test_memcard_icon.py` | `test_vertex_colours_and_light` |  | 0.3 s | Vertex colours and light. |
| `test_memcard_icon.py` | `test_back_faces_are_left_out` |  | 0.1 s | Back faces are left out. |
| `test_memcard_icon.py` | `test_the_texture_and_its_mipmaps` |  | 0.2 s | The texture and its mipmaps. |
| `test_memcard_page.py` | `test_the_cards_and_the_saves` |  | 0.3 s | The cards and the saves. |
| `test_memcard_page.py` | `test_the_slot_is_chosen_in_the_tab` |  | 0.3 s | A card into a slot, which takes it from the card there; out of its slot; written in PCSX2's settings and shown in the list; not while PCSX2 runs. |
| `test_memcard_page.py` | `test_import_export_copy_delete` |  | 1.8 s | Import export copy delete. |
| `test_memcard_page.py` | `test_new_card_format_and_check` |  | 1.6 s | New card format and check. |
| `test_memcard_page.py` | `test_new_card_dialog` |  |  | New card dialog. |
| `test_memcard_page.py` | `test_nothing_written_while_pcsx2_runs` |  | 0.2 s | Nothing written while pcsx2 runs. |
| `test_memcard_page.py` | `test_no_cards_yet` |  | 0.1 s | No cards yet. |
| `test_memcard_page.py` | `test_titles_as_shown` |  |  | Titles as shown. |
| `test_memcard_page.py` | `test_a_delete_asks_first` |  | 0.2 s | A delete asks first. |
| `test_memcards.py` | `test_the_card_folder_and_the_slots` |  |  | The card folder and the slots. |
| `test_memcards.py` | `test_the_cards_pcsx2_lists` |  |  | The cards pcsx2 lists. |
| `test_memcards.py` | `test_the_saves_on_a_card` |  |  | The saves on a card. |
| `test_memcards.py` | `test_import_gives_mymcs_card` | 7 | 0.7 s | Import gives mymcs card. |
| `test_memcards.py` | `test_a_ps1_save_is_listed_with_its_title` |  | 0.1 s | A ps1 save is listed with its title. |
| `test_memcards.py` | `test_delete_gives_mymcs_card` |  | 0.1 s | Delete gives mymcs card. |
| `test_memcards.py` | `test_a_new_card_is_mymcs_format` |  |  | A new card is mymcs format. |
| `test_memcards.py` | `test_export_gives_mymcs_file` | 2 | 0.2 s | Export gives mymcs file. |
| `test_memcards.py` | `test_a_save_already_on_the_card_is_left_alone` |  |  | A save already on the card is left alone. |
| `test_memcards.py` | `test_copy_between_cards` |  | 0.1 s | Copy between cards. |
| `test_memcards.py` | `test_a_card_too_full_gets_nothing` |  |  | A card too full gets nothing. |
| `test_memcards.py` | `test_the_space_is_counted_as_the_card_uses_it` |  | 0.1 s | A save's folder and files in whole clusters, and the card's root folder growing a cluster for every two saves (a deleted save's slot used again first): exactly what the card then has less. |
| `test_memcards.py` | `test_format_keeps_the_size_and_kind` |  | 0.1 s | Format keeps the size and kind. |
| `test_memcards.py` | `test_new_cards_of_every_size` | 4 | 1.2 s | New cards of every size. |
| `test_memcards.py` | `test_new_card_names` |  |  | New card names. |
| `test_memcards.py` | `test_check_finds_a_damaged_page` |  | 1.4 s | Check finds a damaged page. |
| `test_memcards.py` | `test_backups_are_named_by_date_and_the_newest_kept` |  | 0.1 s | Backups are named by date and the newest kept. |
| `test_memcards.py` | `test_pcsx2_running` |  |  | Pcsx2 running. |
| `test_memcards.py` | `test_nothing_is_written_while_pcsx2_runs` |  |  | Nothing is written while pcsx2 runs. |
| `test_memcards.py` | `test_files_that_are_not_saves` |  |  | Files that are not saves. |
| `test_memcards.py` | `test_a_name_with_a_byte_over_127` |  | 0.1 s | mymc++ issue #11: such a name stopped the card being read. |
| `test_memcards.py` | `test_a_save_with_a_folder_in_it_is_deleted` |  |  | _remove_dir added str and bytes for a folder inside a save. |
| `test_memcards.py` | `test_a_failed_import_takes_out_what_it_wrote` |  |  | The card code's own cleanup (without memcards.py counting the space first): the error is the card's, and no half save stays. |
| `test_memcards.py` | `test_an_icon_frame_without_keys` |  |  | mymc++ issue #26: such a frame was read as 16 bytes, and the texture after it was lost. |
| `test_memcards.py` | `test_lzari_never_loads_a_module_from_the_path` |  |  | Lzari never loads a module from the path. |
| `test_memcards.py` | `test_a_max_export_of_a_title_without_ascii` |  | 0.2 s | A title the substitution tables do not cover: ? |
| `test_memcards.py` | `test_the_ecc_code_prints_nothing` |  | 0.7 s | The ecc code prints nothing. |
| `test_memcards.py` | `test_card_sizes_no_card_has` |  |  | Card sizes no card has. |
| `test_pcsx2_settings.py` | `test_a_first_start_gets_pcsx2s_own_defaults` |  |  | No PCSX2.ini yet: PCSX2 2.8.2's defaults (its hotkeys too, which only its reset writes) with what the app owns; a second run changes nothing. |
| `test_pcsx2_settings.py` | `test_the_defaults_hold_nothing_personal` |  |  | The defaults hold nothing personal. |
| `test_pcsx2_settings.py` | `test_an_existing_file_keeps_everything_else` |  |  | An existing file keeps everything else. |
| `test_pcsx2_settings.py` | `test_a_controller_mapped_in_pcsx2_stays` |  |  | A controller mapped in pcsx2 stays. |
| `test_pcsx2_settings.py` | `test_the_bios_is_left_when_it_is_there` |  |  | The bios is left when it is there. |
| `test_pcsx2_settings.py` | `test_no_bios_no_bios_key` |  |  | No bios no bios key. |
| `test_pcsx2_settings.py` | `test_the_ini_is_changed_line_by_line` |  |  | The ini is changed line by line. |
| `test_pcsx2_settings.py` | `test_each_games_screen` |  |  | Each games screen. |
| `test_pcsx2_settings.py` | `test_game_settings_follow_pcsx2s_folder` |  |  | Game settings follow pcsx2s folder. |
| `test_pcsx2_settings.py` | `test_the_settings_of_the_tab` |  |  | Each setting read from PCSX2's defaults while there is no file, written one at a time into a file made from them; a switch on keys that are not true/false (the vibration motors' scale) reads and writes as a switch. |
| `test_pcsx2_settings.py` | `test_player_2_on_the_second_controller` |  |  | Player 2 on the second controller. |
| `test_pcsx2_settings.py` | `test_quit_with_select_and_start` |  |  | Quit with select and start. |
| `test_pcsx2_settings.py` | `test_the_memory_card_slots` |  |  | The memory card slots. |
| `test_run_wrapper.py` | `test_started_by_steam_with_a_real_controller` |  |  | Started by steam with a real controller. |
| `test_run_wrapper.py` | `test_started_by_steam_with_only_steams_controller` |  |  | Started by steam with only steams controller. |
| `test_run_wrapper.py` | `test_started_outside_steam` |  |  | Started outside steam. |
| `test_run_wrapper.py` | `test_started_by_steam_on_a_wayland_desktop` |  |  | Started by steam on a wayland desktop. |
| `test_run_wrapper.py` | `test_without_fusermount_it_unpacks_itself` |  |  | Without fusermount it unpacks itself. |
| `test_run_wrapper.py` | `test_the_game_started_goes_to_the_apps_log` |  |  | One line in the app's log file, in its form, with the game's file name (not its path) and from where; a start without a game (PCSX2's window) says nothing. |
| `test_run_wrapper.py` | `test_not_installed` |  |  | Not installed. |
| `test_run_wrapper.py` | `test_a_game_that_is_gone_is_not_started` |  |  | A shortcut to a game renamed, moved or deleted (owner, 03-11-2026): the emulator is not started, the wrapper says so and ends with 1, so Steam sees the game end; without the app's Python, the words go to stderr alone. |
| `test_settings_page.py` | `test_the_defaults_and_a_change` |  |  | The defaults and a change. |
| `test_settings_page.py` | `test_player_2` |  |  | Player 2. |
| `test_settings_page.py` | `test_quit_with_select_and_start` |  |  | The switch binds PCSX2's shutdown to Select + Start on the first controller and turns PCSX2's question before shutting down off; off again takes the binding out. |
| `test_settings_page.py` | `test_a_value_the_app_does_not_know_is_shown_as_it_is` |  |  | A value the app does not know is shown as it is. |
| `test_settings_page.py` | `test_nothing_written_while_pcsx2_runs` |  |  | Nothing written while pcsx2 runs. |
| `test_settings_page.py` | `test_every_setting_has_a_widget_of_its_kind` |  |  | Every setting has a widget of its kind. |
| `test_settings_page.py` | `test_bazzites_volume_for_pcsx2` |  |  | Beside PCSX2's volume: the volume Bazzite remembers for PCSX2, as the window passes it (core's sound); muted or turned down to nothing is a problem, said in words. |
| `test_shortcuts.py` | `test_the_launch_line_and_whose_shortcut_it_is` |  |  | The launch line and whose shortcut it is. |
| `test_shortcuts.py` | `test_names_are_unique` |  |  | Names are unique. |
| `test_shortcuts.py` | `test_add_then_take_out` |  | 0.6 s | Add then take out. |
| `test_shortcuts.py` | `test_a_shortcut_taken_out_under_the_name_it_has` |  |  | A shortcut taken out under the name it has. |
| `test_shortcuts.py` | `test_the_drawn_artwork` |  | 0.3 s | The drawn artwork. |
| `test_shortcuts.py` | `test_pictures_from_steamgriddb_in_place_of_the_drawn_ones` |  | 0.9 s | All four from SteamGridDB: a PS2 disc brings none. |
| `test_userdata.py` | `test_pcsx2s_own_folder` |  |  | Pcsx2s own folder. |
| `test_userdata.py` | `test_the_bios_dumps` |  |  | The bios dumps. |
| `test_userdata.py` | `test_a_dump_is_removed_with_its_files` |  |  | A dump is removed with its files. |
| `test_userdata.py` | `test_pcsx2s_last_run` |  |  | The log's version, game, controllers (each once) and the play time PCSX2 counted; without that line (PCSX2 did not shut down by itself) the last time stamp; without a log nothing. |
| `test_userdata.py` | `test_pcsx2s_play_times` |  |  | Pcsx2s play times. |
| `test_userdata.py` | `test_a_play_time_in_words` |  |  | A play time in words. |

## apps/ppsspp

91 tests in 11 files, 4.5 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_emulator.py` | `test_the_pin_points_at_the_release` |  |  | The pin points at the release. |
| `test_emulator.py` | `test_install_and_remove` |  |  | Install and remove. |
| `test_emulator.py` | `test_an_older_version_is_replaced` |  |  | An older version is replaced. |
| `test_emulator.py` | `test_a_different_file_is_refused` |  |  | A different file is refused. |
| `test_emulator.py` | `test_a_failed_install_keeps_the_installed_one` |  |  | A failed install keeps the installed one. |
| `test_emulator.py` | `test_download_errors_say_what_happened` |  |  | Download errors say what happened. |
| `test_emulator.py` | `test_ppsspp_tags_with_two_or_three_numbers` |  |  | Ppsspp tags with two or three numbers. |
| `test_emulator.py` | `test_a_newer_ppsspp_release` |  |  | A newer ppsspp release. |
| `test_games.py` | `test_param_sfo_is_read` |  |  | Param sfo is read. |
| `test_games.py` | `test_ppsspps_own_folder` |  |  | Ppsspps own folder. |
| `test_games.py` | `test_an_iso_is_read` |  |  | An iso is read. |
| `test_games.py` | `test_a_cso_holds_the_same_iso` |  |  | A cso holds the same iso. |
| `test_games.py` | `test_a_cso_with_an_alignment` |  |  | A cso with an alignment. |
| `test_games.py` | `test_files_that_are_no_psp_games` |  |  | Files that are no psp games. |
| `test_games.py` | `test_a_chd_is_listed_under_its_name` |  |  | A chd is listed under its name. |
| `test_games.py` | `test_a_memory_stick_game_and_an_update` |  |  | A memory stick game and an update. |
| `test_games.py` | `test_a_title_with_line_breaks` |  |  | A title with line breaks. |
| `test_games.py` | `test_the_memory_stick_games` |  |  | The memory stick games. |
| `test_games.py` | `test_scan_finds_games_sorted_once_and_not_too_deep` |  |  | Scan finds games sorted once and not too deep. |
| `test_games.py` | `test_the_games_own_pictures` |  |  | The games own pictures. |
| `test_games.py` | `test_a_pbp_part_by_name` |  |  | A pbp part by name. |
| `test_games.py` | `test_a_failing_card_ends_no_scan` |  |  | A failing card ends no scan. |
| `test_library.py` | `test_fixed_folders` |  |  | Fixed folders. |
| `test_library.py` | `test_removal_rows` |  |  | Removal rows. |
| `test_main_window.py` | `test_ppsspp_is_set_up_once_installed` |  | 0.1 s | Once PPSSPP is installed, and while it does not run, the app turns its notice of a newer release off in ppsspp.ini (owner, 03-11-2026); the Log tab says so once, and nothing is written while PPSSPP runs. |
| `test_main_window.py` | `test_no_user_name_on_the_screen` |  |  | The user's folders show as ~ (owner, 03-11-2026: the privacy rule): the memory stick and the game folders on the first step, and a message with a path in it. |
| `test_main_window.py` | `test_before_installing` |  |  | Before installing. |
| `test_main_window.py` | `test_installed_with_games` |  |  | Installed with games. |
| `test_main_window.py` | `test_the_apps_own_game_folders` |  |  | The games are put in Games/PSP in the home folder, made when the app opens, and in Games/PSP on a removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); no folder is chosen or remembered any more. |
| `test_main_window.py` | `test_rename_files_needs_a_disc_image` |  |  | Rename files needs a disc image. |
| `test_main_window.py` | `test_a_chd_is_marked` |  |  | A chd is marked. |
| `test_main_window.py` | `test_install_runs_off_the_window` |  | 0.1 s | Install runs off the window. |
| `test_main_window.py` | `test_ppsspps_window` |  | 0.1 s | PPSSPP settings opens PPSSPP's own window, through the run wrapper and without a game. |
| `test_main_window.py` | `test_the_steam_link` |  |  | The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the boxes and Start game do, and Steam in it is a link the app opens itself. |
| `test_main_window.py` | `test_steam_added_and_taken_out` |  | 0.3 s | Steam added and taken out. |
| `test_main_window.py` | `test_a_shortcut_named_before_the_system_prefix_is_renamed` |  | 0.3 s | A shortcut named by the title alone, as before "[PSP] ": Update Steam is on for it and renames it, with its play time; the artwork under its old number goes. |
| `test_main_window.py` | `test_a_shortcut_of_a_game_no_longer_found_is_taken_out` |  |  | A shortcut of a game no longer found is taken out. |
| `test_main_window.py` | `test_no_steam_game_mode_or_no_wrapper` |  | 0.1 s | No steam game mode or no wrapper. |
| `test_main_window.py` | `test_the_blue_look` |  |  | RPCS3 Manager's design (owner, 07-11-2026): the Refresh pill and the boxes in the header, the action pills under the introduction, the tabs. |
| `test_main_window.py` | `test_a_newer_ppsspp_is_mentioned` |  | 0.1 s | A newer ppsspp is mentioned. |
| `test_main_window.py` | `test_another_ppsspp_is_installed` |  |  | Another release than the app brings: the line stays the state, the tip says Install puts the app's in, and the log says it once. |
| `test_main_window.py` | `test_the_log_tab` |  |  | What the window says goes to the Log tab with the time, after what the log file held already. |
| `test_main_window.py` | `test_clear_logs_empties_the_log` |  |  | Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones beside it removed and the Log tab emptied with them, the open page kept. |
| `test_main_window.py` | `test_the_play_time_ppsspp_counts` |  |  | Play time, the last pill of the second row (owner, 18-11-2026: the header is full): all games together, from [PlayTime] in PPSSPP's settings, each game's time in the tip under its title. |
| `test_main_window.py` | `test_the_window_keeps_its_width` |  |  | The window's width (owner, 18-11-2026): 900 when it opens, which is also its narrowest, and what is in it asks for no more than the header's four pills do; the six tabs share the whole width, the last one up to the margin; under the header's pills the two links alone, in the type of a pill's caption, each still a link. |
| `test_main_window.py` | `test_covers_with_the_suites_key` |  | 0.5 s | Steam artwork… keeps the suite's key; Update Steam then looks up the games and puts the cover on the portrait, and a game in Steam not looked up yet makes the button do something again. |
| `test_main_window.py` | `test_remove_game_asks_what_to_keep` |  | 0.1 s | Remove game… (owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked deletes the rows still ticked off the window's thread and says what went and what stayed. |
| `test_main_window.py` | `test_the_settings_tab` |  |  | The Settings tab holds PPSSPP's settings in the app (core's settings_page): the values as ppsspp.ini holds them, a change written into it at once, and nothing while PPSSPP runs. |
| `test_main_window.py` | `test_start_game_starts_the_chosen_game_through_steam` |  | 0.3 s | The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your games through Steam, by its shortcut's number, and the open tab stays open. |
| `test_main_window.py` | `test_the_controller_state_beside_the_title` |  |  | Controller connected or No controller (owner, 18-11-2026: as the other managers show it), from the kernel's list of input devices, looked at again every few seconds; Steam's own virtual controller does not count. |
| `test_ppsspp_settings.py` | `test_the_values_as_ppsspp_writes_them` |  |  | The values as ppsspp writes them. |
| `test_ppsspp_settings.py` | `test_the_defaults_without_a_file` |  |  | The defaults without a file. |
| `test_ppsspp_settings.py` | `test_other_forms_of_a_value` |  |  | Other forms of a value. |
| `test_ppsspp_settings.py` | `test_a_setting_is_written_with_the_rest_of_the_file` |  |  | A setting is written with the rest of the file. |
| `test_ppsspp_settings.py` | `test_the_on_screen_switches_are_bits_of_one_number` |  |  | The on screen switches are bits of one number. |
| `test_ppsspp_settings.py` | `test_the_groups_and_the_defaults` |  |  | The groups and the defaults. |
| `test_rename_dialog.py` | `test_the_table_and_the_template` |  |  | The table and the template. |
| `test_rename_dialog.py` | `test_another_apps_template_is_not_adopted` |  |  | Another apps template is not adopted. |
| `test_rename_dialog.py` | `test_translation_and_pictures` |  |  | Translation and pictures. |
| `test_rename_dialog.py` | `test_rename_all` |  |  | Rename all. |
| `test_rename_dialog.py` | `test_a_name_that_is_taken` |  |  | A name that is taken. |
| `test_rename_dialog.py` | `test_without_pictures_the_label_says_which` |  |  | Without pictures the label says which. |
| `test_renamer.py` | `test_formatted_name_templates` | 8 |  | Formatted name templates. |
| `test_renamer.py` | `test_formatted_name_cleans_and_prefers_the_translation` |  |  | Formatted name cleans and prefers the translation. |
| `test_renamer.py` | `test_what_may_be_renamed` |  |  | What may be renamed. |
| `test_renamer.py` | `test_rename_file` |  |  | Rename file. |
| `test_run_wrapper.py` | `test_started_by_steam_with_a_real_controller` |  |  | Started by steam with a real controller. |
| `test_run_wrapper.py` | `test_started_by_steam_with_only_steams_controller` |  |  | Started by steam with only steams controller. |
| `test_run_wrapper.py` | `test_started_outside_steam` |  |  | Started outside steam. |
| `test_run_wrapper.py` | `test_started_by_steam_on_a_wayland_desktop` |  |  | Started by steam on a wayland desktop. |
| `test_run_wrapper.py` | `test_without_fusermount_it_unpacks_itself` |  |  | Without fusermount it unpacks itself. |
| `test_run_wrapper.py` | `test_not_installed` |  |  | Not installed. |
| `test_run_wrapper.py` | `test_a_game_that_is_gone_is_not_started` |  |  | A shortcut to a game renamed, moved or deleted (owner, 03-11-2026): the emulator is not started, the wrapper says so and ends with 1, so Steam sees the game end; without the app's Python, the words go to stderr alone. |
| `test_saves.py` | `test_the_saves_are_read_from_their_folders` |  |  | The saves are read from their folders. |
| `test_saves.py` | `test_export_and_import_again` |  |  | Export and import again. |
| `test_saves.py` | `test_a_zip_with_the_files_at_the_top_takes_its_own_name` |  |  | A zip with the files at the top takes its own name. |
| `test_saves.py` | `test_what_is_no_save_is_refused` |  |  | What is no save is refused. |
| `test_saves.py` | `test_delete` |  |  | Delete. |
| `test_saves.py` | `test_the_tab_lists_the_saves_with_the_picture` |  |  | The tab lists the saves with the picture. |
| `test_saves.py` | `test_the_tab_exports_imports_and_deletes` |  |  | The tab exports imports and deletes. |
| `test_saves.py` | `test_nothing_is_changed_while_ppsspp_runs` |  |  | Nothing is changed while ppsspp runs. |
| `test_shortcuts.py` | `test_the_launch_line_and_whose_shortcut_it_is` |  |  | The launch line and whose shortcut it is. |
| `test_shortcuts.py` | `test_names_are_unique` |  |  | Names are unique. |
| `test_shortcuts.py` | `test_add_then_take_out` |  | 0.4 s | Add then take out. |
| `test_shortcuts.py` | `test_a_shortcut_taken_out_under_the_name_it_has` |  |  | A shortcut taken out under the name it has. |
| `test_shortcuts.py` | `test_artwork_sizes_with_and_without_the_games_pictures` |  | 0.8 s | Artwork sizes with and without the games pictures. |
| `test_shortcuts.py` | `test_a_cover_from_steamgriddb_in_place_of_the_drawn_portrait` |  | 0.5 s | A cover from steamgriddb in place of the drawn portrait. |
| `test_userdata.py` | `test_prepare_turns_the_notice_off_and_keeps_the_rest` |  |  | Prepare turns the notice off and keeps the rest. |
| `test_userdata.py` | `test_the_byte_order_mark_ppsspp_writes_is_kept` |  |  | PPSSPP writes the file with a UTF-8 byte order mark: the first section is still found behind it, and the mark stays. |
| `test_userdata.py` | `test_ini_lines` |  |  | Ini lines. |
| `test_userdata.py` | `test_ppsspp_running_sees_the_appimages_process` |  |  | Ppsspp running sees the appimages process. |

## apps/quickfix

38 tests in 6 files.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_catalog.py` | `test_the_portal_lists_every_quickfix` |  |  | The portal lists every quickfix. |
| `test_catalog.py` | `test_the_groups_are_board_tests_installers` |  |  | The groups are board tests installers. |
| `test_catalog.py` | `test_how_follows_ostree` |  |  | How follows ostree. |
| `test_kargs.py` | `test_split_and_join_keep_the_line` |  |  | Split and join keep the line. |
| `test_kargs.py` | `test_every_argument_of_the_ps5_lines_is_described` |  |  | Every argument of the ps5 lines is described. |
| `test_kargs.py` | `test_the_add_menu_and_the_list` |  |  | The add menu and the list. |
| `test_main_window.py` | `test_version_is_the_single_source` |  |  | Version is the single source. |
| `test_main_window.py` | `test_icons_are_beside_the_package` |  |  | Icons are beside the package. |
| `test_main_window.py` | `test_window_lists_every_quickfix_and_opens_one` |  |  | Window lists every quickfix and opens one. |
| `test_state.py` | `test_mangohud_logging_lines` |  |  | Mangohud logging lines. |
| `test_state.py` | `test_log_files` |  |  | Log files. |
| `test_state.py` | `test_mapcount_and_journal` |  |  | Mapcount and journal. |
| `test_state.py` | `test_cmdline` |  |  | Cmdline. |
| `test_state.py` | `test_find_tool_where_the_tests_look` |  |  | Find tool where the tests look. |
| `test_state.py` | `test_board_tests_installer` |  |  | Board tests installer. |
| `test_system.py` | `test_mapcount_on_and_off` |  |  | Mapcount on and off. |
| `test_system.py` | `test_journal_on_and_off_only_its_own` |  |  | Journal on and off only its own. |
| `test_system.py` | `test_the_command_and_its_answer` |  |  | The command and its answer. |
| `test_system.py` | `test_cmdline_save_keeps_a_backup` |  |  | Cmdline save keeps a backup. |
| `test_system.py` | `test_cmdline_refuses_a_line_that_would_not_boot` |  |  | Cmdline refuses a line that would not boot. |
| `test_system.py` | `test_cmdline_saves_a_fallback_line` |  |  | Cmdline saves a fallback line. |
| `test_system.py` | `test_cmdline_without_the_loaders_partition` |  |  | Cmdline without the loaders partition. |
| `test_system.py` | `test_the_changes_take_only_their_own_states` |  |  | The changes take only their own states. |
| `test_windows.py` | `test_quickfix_lists_and_installs` |  |  | Quickfix lists and installs. |
| `test_windows.py` | `test_mangohud_config_made_and_logging_set` |  |  | Mangohud config made and logging set. |
| `test_windows.py` | `test_mangohud_deletes_only_old_logs` |  |  | Mangohud deletes only old logs. |
| `test_windows.py` | `test_game_memory_map` |  |  | Game memory map. |
| `test_windows.py` | `test_persistent_journal_asks_before_it_removes` |  |  | Persistent journal asks before it removes. |
| `test_windows.py` | `test_boot_command_line_shows_every_argument_with_what_it_does` |  |  | Boot command line shows every argument with what it does. |
| `test_windows.py` | `test_boot_command_line_edits_adds_moves_and_removes_rows` |  |  | Boot command line edits adds moves and removes rows. |
| `test_windows.py` | `test_boot_command_line_opens_the_fallback_lines` |  |  | Boot command line opens the fallback lines. |
| `test_windows.py` | `test_boot_command_line_no_drops_the_edits_cancel_keeps_them` |  |  | Boot command line no drops the edits cancel keeps them. |
| `test_windows.py` | `test_boot_command_line_will_not_save_a_line_that_would_not_boot` |  |  | Boot command line will not save a line that would not boot. |
| `test_windows.py` | `test_boot_command_line_a_failed_save_keeps_the_edits` |  |  | Boot command line a failed save keeps the edits. |
| `test_windows.py` | `test_boot_command_line_reads_a_locked_file_with_the_password` |  |  | Boot command line reads a locked file with the password. |
| `test_windows.py` | `test_a_canceled_password_says_so` |  |  | A canceled password says so. |
| `test_windows.py` | `test_every_window_says_what_it_does` |  |  | Every window says what it does. |
| `test_windows.py` | `test_the_system_part_runs_from_the_app` |  |  | The system part runs from the app. |

## apps/remoteplay

240 tests in 25 files, 9.6 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_consoles.py` | `test_store_round_trip_and_mode` |  |  | Store round trip and mode. |
| `test_consoles.py` | `test_put_replaces_the_same_console` |  |  | Put replaces the same console. |
| `test_consoles.py` | `test_remove` |  |  | Remove. |
| `test_consoles.py` | `test_a_broken_file_or_entry_is_skipped` |  |  | A broken file or entry is skipped. |
| `test_consoles.py` | `test_key_falls_back_to_the_mac` |  |  | Key falls back to the mac. |
| `test_consoles.py` | `test_account_id_forms` | 3 |  | Account id forms. |
| `test_consoles.py` | `test_bad_account_ids` | 6 |  | Bad account ids. |
| `test_consoles.py` | `test_account_id_round_trip` |  |  | Account id round trip. |
| `test_consoles.py` | `test_pins` |  |  | Pins. |
| `test_controller_test.py` | `test_the_controller_test` |  | 0.1 s | The controller test. |
| `test_controller_test.py` | `test_without_a_controller` |  |  | Without a controller. |
| `test_controller_test.py` | `test_a_controller_that_is_not_sony` |  |  | A controller that is not sony. |
| `test_direct.py` | `test_find_console` |  |  | Find console. |
| `test_direct.py` | `test_a_console_that_is_on` |  |  | A console that is on. |
| `test_direct.py` | `test_a_console_in_rest_mode_is_woken` |  |  | A console in rest mode is woken. |
| `test_direct.py` | `test_a_console_that_stays_in_rest_mode` |  |  | A console that stays in rest mode. |
| `test_direct.py` | `test_a_console_at_another_address_is_found_by_its_host_id` |  |  | A console at another address is found by its host id. |
| `test_direct.py` | `test_a_console_that_does_not_answer` |  |  | A console that does not answer. |
| `test_direct.py` | `test_the_direct_stream` |  | 0.3 s | The direct stream. |
| `test_direct.py` | `test_the_direct_stream_without_the_console` |  |  | The direct stream without the console. |
| `test_direct.py` | `test_run_with_an_unknown_console` |  |  | Run with an unknown console. |
| `test_direct.py` | `test_closing_waits_for_the_stream_to_close` |  | 0.3 s | Closing waits for the stream to close. |
| `test_discovery.py` | `test_srch_packets_are_the_references` |  |  | Srch packets are the references. |
| `test_discovery.py` | `test_wakeup_packet_carries_the_key_as_a_number` |  |  | Wakeup packet carries the key as a number. |
| `test_discovery.py` | `test_wakeup_needs_a_usable_key` | 3 |  | Wakeup needs a usable key. |
| `test_discovery.py` | `test_parse_standby_ps5` |  |  | Parse standby ps5. |
| `test_discovery.py` | `test_parse_ready_ps4` |  |  | Parse ready ps4. |
| `test_discovery.py` | `test_target_from_system_version` | 6 |  | Target from system version. |
| `test_discovery.py` | `test_search_finds_a_ps5_through_its_own_port` |  | 0.5 s | Search finds a ps5 through its own port. |
| `test_discovery.py` | `test_search_finds_a_ps4_in_rest_mode` |  | 0.5 s | Search finds a ps4 in rest mode. |
| `test_discovery.py` | `test_search_with_nobody_there_returns_nothing` |  | 0.3 s | Search with nobody there returns nothing. |
| `test_discovery.py` | `test_wake_sends_the_packet_to_the_console` |  |  | Wake sends the packet to the console. |
| `test_discovery.py` | `test_software_version_of_a_ps4` |  |  | Software version of a ps4. |
| `test_exit_keys.py` | `test_unhandled_escape_from_child_closes_window` |  |  | Unhandled escape from child closes window. |
| `test_exit_keys.py` | `test_handled_and_modified_escape_do_not_close` |  |  | Handled and modified escape do not close. |
| `test_exit_keys.py` | `test_dialog_keeps_qt_escape` |  |  | Dialog keeps qt escape. |
| `test_exit_keys.py` | `test_menu_keeps_qt_escape` |  |  | Menu keeps qt escape. |
| `test_exit_keys.py` | `test_close_can_be_refused_and_repeat_is_ignored` |  |  | Close can be refused and repeat is ignored. |
| `test_exit_keys.py` | `test_escape_leaves_fullscreen_without_closing_stream` |  |  | Escape leaves fullscreen without closing stream. |
| `test_gamepad.py` | `test_idle` |  |  | Idle. |
| `test_gamepad.py` | `test_buttons_as_the_reference_maps_them` | 19 |  | Buttons as the reference maps them. |
| `test_gamepad.py` | `test_axes` |  |  | Axes. |
| `test_gamepad.py` | `test_several_controllers_combine` |  |  | Several controllers combine. |
| `test_gamepad.py` | `test_touchpad_scaled_to_the_console` | 2 |  | Touchpad scaled to the console. |
| `test_gamepad.py` | `test_touch_ids_as_the_reference_gives_them` |  |  | Touch ids as the reference gives them. |
| `test_gamepad.py` | `test_reader_sends_each_change_once` |  |  | Reader sends each change once. |
| `test_gamepad.py` | `test_a_controller_that_comes_later_and_one_that_goes_while_held` |  |  | A controller that comes later and one that goes while held. |
| `test_gamepad.py` | `test_without_sdl_the_log_says_so` |  |  | Without sdl the log says so. |
| `test_gamepad.py` | `test_motion_as_the_reference_feeds_it` |  |  | Motion as the reference feeds it. |
| `test_gamepad.py` | `test_motion_of_the_first_controller_that_moves` |  |  | Motion of the first controller that moves. |
| `test_gamepad.py` | `test_reader_passes_the_motion_on` |  |  | Reader passes the motion on. |
| `test_gamepad.py` | `test_without_the_core_no_motion` |  |  | Without the core no motion. |
| `test_gamepad.py` | `test_motion_reset_makes_the_current_position_the_rest` |  |  | Motion reset makes the current position the rest. |
| `test_gamepad.py` | `test_reader_drives_the_controllers` |  |  | Reader drives the controllers. |
| `test_gamepad.py` | `test_reader_resets_the_motion` |  |  | Reader resets the motion. |
| `test_gamepad.py` | `test_steams_virtual_controller_only_when_alone` |  |  | Steams virtual controller only when alone. |
| `test_gamepad.py` | `test_steams_ignore_list_is_undone` |  |  | Steams ignore list is undone. |
| `test_gamepad.py` | `test_a_missing_library_is_a_gamepad_error` |  |  | A missing library is a gamepad error. |
| `test_gamepad.py` | `test_real_sdl_opens_and_closes` |  |  | Real sdl opens and closes. |
| `test_gamepad.py` | `test_player_experiment_keeps_the_second_controller_apart` |  |  | Player experiment keeps the second controller apart. |
| `test_genuine.py` | `test_the_owners_dualshock4_over_bluetooth` |  |  | The owners dualshock4 over bluetooth. |
| `test_genuine.py` | `test_over_usb_the_calibration_comes_in_the_other_order` |  |  | Over usb the calibration comes in the other order. |
| `test_genuine.py` | `test_what_a_copy_gets_wrong` | 8 |  | What a copy gets wrong. |
| `test_genuine.py` | `test_a_dualsense` |  |  | A dualsense. |
| `test_genuine.py` | `test_other_controllers_are_not_checked` |  |  | Other controllers are not checked. |
| `test_history.py` | `test_store_adds_up_per_console_and_game` |  |  | Store adds up per console and game. |
| `test_history.py` | `test_store_skips_a_broken_entry` |  |  | Store skips a broken entry. |
| `test_history.py` | `test_duration` |  |  | Duration. |
| `test_history.py` | `test_tracker_credits_the_time_between_answers` |  |  | Tracker credits the time between answers. |
| `test_history.py` | `test_tracker_runs_beside_the_stream` |  |  | Tracker runs beside the stream. |
| `test_history.py` | `test_watch_stream_keeps_the_history` |  |  | Watch stream keeps the history. |
| `test_history.py` | `test_dialog_lists_newest_first_and_clears` |  |  | Dialog lists newest first and clears. |
| `test_main_window.py` | `test_opens_empty` |  |  | Opens empty. |
| `test_main_window.py` | `test_search_lists_both_consoles` |  |  | Search lists both consoles. |
| `test_main_window.py` | `test_search_at_an_address_is_remembered` |  |  | Search at an address is remembered. |
| `test_main_window.py` | `test_register_needs_a_selection_and_valid_input` |  |  | Register needs a selection and valid input. |
| `test_main_window.py` | `test_register_stores_the_console` |  |  | Register stores the console. |
| `test_main_window.py` | `test_registered_consoles_are_loaded` |  |  | Registered consoles are loaded. |
| `test_main_window.py` | `test_a_console_with_a_new_address_is_updated` |  |  | A console with a new address is updated. |
| `test_main_window.py` | `test_personal_details_are_masked_until_shown` |  |  | Personal details are masked until shown. |
| `test_main_window.py` | `test_wake_test_and_rest` |  |  | Wake test and rest. |
| `test_main_window.py` | `test_stream_window` |  |  | Stream window. |
| `test_main_window.py` | `test_closing_the_main_window_stops_the_stream` |  |  | Closing the main window stops the stream. |
| `test_main_window.py` | `test_passcode_and_remove` |  |  | Passcode and remove. |
| `test_main_window.py` | `test_stream_settings_are_kept_with_the_console` |  |  | Stream settings are kept with the console. |
| `test_main_window.py` | `test_buttons_are_off_while_a_job_runs` |  |  | Buttons are off while a job runs. |
| `test_main_window.py` | `test_jobs_against_the_fake_console` |  | 0.1 s | jobs.py end to end: registration and a test session against the fake console on localhost. |
| `test_main_window.py` | `test_find_account_id_fills_the_field` |  |  | Find account id fills the field. |
| `test_main_window.py` | `test_account_dialog` |  |  | Account dialog. |
| `test_main_window.py` | `test_account_dialog_takes_the_redirect_from_the_clipboard` |  |  | Account dialog takes the redirect from the clipboard. |
| `test_main_window.py` | `test_steam_ps_button_setting` |  |  | Steam ps button setting. |
| `test_main_window.py` | `test_steam_setting_hidden_without_steam_and_off_in_game_mode` |  |  | Steam setting hidden without steam and off in game mode. |
| `test_main_window.py` | `test_controller_test_opens_from_the_window` |  |  | Controller test opens from the window. |
| `test_main_window.py` | `test_history_opens_from_the_window` |  |  | History opens from the window. |
| `test_main_window.py` | `test_add_to_game_mode` |  |  | Add to game mode. |
| `test_main_window.py` | `test_remove_offers_to_remove_the_game_mode_shortcut` |  |  | Remove offers to remove the game mode shortcut. |
| `test_main_window.py` | `test_console_box_shows_model_software_and_what_runs` |  |  | Console box shows model software and what runs. |
| `test_main_window.py` | `test_settings_box_opens_the_app_settings` |  |  | Settings box opens the app settings. |
| `test_main_window.py` | `test_address_field_searches_on_enter` |  |  | Address field searches on enter. |
| `test_main_window.py` | `test_the_window_looks_like_the_other_gaming_apps` |  |  | As the shadPS4 Manager (owner, 20-10-2026): the gaming blue, numbered steps with their buttons the same size, Settings… in the header, both lists as tables with a blue header, Stream the filled main button; a double click on a registered console streams it. |
| `test_native.py` | `test_gkcrypt` |  |  | Gkcrypt. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_ecdh` |  |  | Ecdh. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_ecdh_both_sides_agree_and_bad_keys` |  |  | Ecdh both sides agree and bad keys. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_packet_mac_and_verify` |  |  | Packet mac and verify. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_av_parse` |  |  | Av parse. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_av_parse_refuses_short_and_unknown` |  |  | Av parse refuses short and unknown. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_congestion_and_key_state` |  |  | Congestion and key state. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_handshake_messages` |  |  | Handshake messages. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_data_and_ack` |  |  | Data and ack. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_v7_header` |  |  | V7 header. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_fec` |  |  | Fec. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_audio_decoder` |  |  | Audio decoder. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_decoder` |  |  | Decoder. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_native.py` | `test_orientation_tracker_matches_reference` |  |  | The tracker as the module gives it, against the reference's orientation.c (orientation_vectors.json). (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_privacy.py` | `test_account_id_keeps_its_last_4` | 4 |  | Account id keeps its last 4. |
| `test_privacy.py` | `test_address_keeps_its_last_part` | 4 |  | Address keeps its last part. |
| `test_privacy.py` | `test_masker_hides_what_it_knows` |  |  | Masker hides what it knows. |
| `test_privacy.py` | `test_masker_hides_by_shape` |  |  | Masker hides by shape. |
| `test_privacy.py` | `test_name_mask_hides_the_length` |  |  | Name mask hides the length. |
| `test_psn.py` | `test_login_url_is_the_references` |  |  | Login url is the references. |
| `test_psn.py` | `test_code_from_the_pasted_address` |  |  | Code from the pasted address. |
| `test_psn.py` | `test_account_id_from_psn` |  | 0.5 s | Account id from psn. |
| `test_psn.py` | `test_used_or_old_code` |  | 0.5 s | Used or old code. |
| `test_psn.py` | `test_answer_without_account_id` |  | 0.5 s | Answer without account id. |
| `test_psn.py` | `test_psn_unreachable` |  |  | Psn unreachable. |
| `test_psn.py` | `test_job` |  | 0.5 s | Job. |
| `test_regist.py` | `test_register_with_the_console` | 3 |  | Register with the console. |
| `test_regist.py` | `test_wrong_pin_is_reported` |  |  | Wrong pin is reported. |
| `test_regist.py` | `test_wrong_account_is_reported` |  |  | Wrong account is reported. |
| `test_regist.py` | `test_no_console_at_the_address` |  | 2.0 s | No console at the address. |
| `test_regist.py` | `test_payload_layout` |  |  | Payload layout. |
| `test_regist.py` | `test_request_header_is_the_references` |  |  | Request header is the references. |
| `test_regist.py` | `test_answer_without_keys_is_refused` |  |  | Answer without keys is refused. |
| `test_regist.py` | `test_account_id_must_have_8_bytes` |  |  | Account id must have 8 bytes. |
| `test_rpcrypt.py` | `test_session_crypto_matches_reference` | 15 |  | Session crypto matches reference. |
| `test_rpcrypt.py` | `test_regist_crypto_matches_reference` | 15 |  | Regist crypto matches reference. |
| `test_rpcrypt.py` | `test_the_vectors_cover_every_known_target` |  |  | The vectors cover every known target. |
| `test_rpcrypt.py` | `test_decrypt_undoes_encrypt_for_any_length` | 6 |  | Decrypt undoes encrypt for any length. |
| `test_rpcrypt.py` | `test_each_counter_gives_its_own_keystream` |  |  | Each counter gives its own keystream. |
| `test_rpcrypt.py` | `test_hmac_key_per_target` |  |  | Hmac key per target. |
| `test_rpcrypt.py` | `test_table_sizes` |  |  | Table sizes. |
| `test_rpcrypt.py` | `test_regist_key_offset_is_checked` |  |  | Regist key offset is checked. |
| `test_rpcrypt.py` | `test_bright_ambassador_uses_the_whole_nonce_range` |  |  | Bright ambassador uses the whole nonce range. |
| `test_senkusha.py` | `test_messages_match_reference` | 7 |  | Messages match reference. |
| `test_senkusha.py` | `test_console_answers_decode` |  |  | Console answers decode. |
| `test_senkusha.py` | `test_rtt_for_the_launch_spec` |  |  | Rtt for the launch spec. |
| `test_senkusha.py` | `test_full_run` |  |  | Full run. (Skipped here.) |
| `test_senkusha.py` | `test_mtu_search_finds_the_limits` |  |  | Mtu search finds the limits. (Skipped here.) |
| `test_senkusha.py` | `test_no_pongs` |  |  | No pongs. (Skipped here.) |
| `test_senkusha.py` | `test_no_client_mtu_answer` |  |  | No client mtu answer. (Skipped here.) |
| `test_senkusha.py` | `test_nothing_on_the_port` |  |  | Nothing on the port. (Skipped here.) |
| `test_session.py` | `test_session_starts_and_answers_heartbeats` | 2 | 0.4 s | Session starts and answers heartbeats. |
| `test_session.py` | `test_version_mismatch_is_retried_with_the_consoles_version` |  |  | Version mismatch is retried with the consoles version. |
| `test_session.py` | `test_login_passcode_is_sent_when_asked` |  | 0.1 s | Login passcode is sent when asked. |
| `test_session.py` | `test_login_passcode_missing` |  |  | Login passcode missing. |
| `test_session.py` | `test_wrong_login_passcode` |  |  | Wrong login passcode. |
| `test_session.py` | `test_unusual_session_id_gets_a_made_up_one` |  |  | Unusual session id gets a made up one. |
| `test_session.py` | `test_invalid_session_id_from_a_ps4` |  |  | Recorded from the owner's PS4 Pro: the length byte, then the text InvalidSessionId. |
| `test_session.py` | `test_goto_bed_reaches_the_console` |  | 0.2 s | Goto bed reaches the console. |
| `test_session.py` | `test_no_console` |  |  | No console. |
| `test_session.py` | `test_frame_layout` |  |  | Frame layout. |
| `test_sound.py` | `test_reads_in_order_and_whole_samples` |  |  | Reads in order and whole samples. |
| `test_sound.py` | `test_empty_gives_silence_of_at_most_10_ms` |  |  | Empty gives silence of at most 10 ms. |
| `test_sound.py` | `test_piling_up_drops_the_oldest` |  |  | Piling up drops the oldest. |
| `test_sound.py` | `test_device_reads_the_buffer` |  |  | Device reads the buffer. |
| `test_sound.py` | `test_player_without_an_audio_output` |  |  | Player without an audio output. |
| `test_sound.py` | `test_audio_delay_holds_the_sound_back` |  |  | Audio delay holds the sound back. |
| `test_sound.py` | `test_player_takes_the_settings` |  |  | Player takes the settings. |
| `test_steam_env.py` | `test_started_by_steam_the_app_starts_again_without_its_libraries` |  |  | Started by steam the app starts again without its libraries. |
| `test_steam_env.py` | `test_steams_overlay_is_left_and_the_rest_kept` |  |  | Steams overlay is left and the rest kept. |
| `test_steam_env.py` | `test_once_only_and_not_without_steam` |  |  | Once only and not without steam. |
| `test_steam_env.py` | `test_x11_in_game_mode` |  |  | X11 in game mode. |
| `test_steam_settings.py` | `test_find_steam` |  |  | Find steam. |
| `test_steam_settings.py` | `test_read` | 6 |  | Read. |
| `test_steam_settings.py` | `test_write_keeps_the_rest_of_the_file` |  |  | Write keeps the rest of the file. |
| `test_steam_settings.py` | `test_change_while_steam_runs` |  |  | Change while steam runs. |
| `test_steam_settings.py` | `test_steam_that_does_not_close_changes_nothing` |  |  | Steam that does not close changes nothing. |
| `test_steam_settings.py` | `test_change_without_steam_running` |  |  | Change without steam running. |
| `test_steam_settings.py` | `test_game_mode_changes_nothing` |  |  | Game mode changes nothing. |
| `test_steam_settings.py` | `test_steam_running_reads_process_names` |  |  | Steam running reads process names. |
| `test_steam_settings.py` | `test_a_steam_command_leaves_no_zombie` |  |  | A steam command leaves no zombie. |
| `test_steam_settings.py` | `test_job_says_what_happened` |  |  | Job says what happened. |
| `test_steam_shortcuts.py` | `test_the_binary_format_by_hand` |  |  | The binary format by hand. |
| `test_steam_shortcuts.py` | `test_appid_is_steams_crc` |  |  | Appid is steams crc. |
| `test_steam_shortcuts.py` | `test_add_update_and_remove` |  |  | Add update and remove. |
| `test_steam_shortcuts.py` | `test_a_first_shortcut_and_no_users` |  |  | A first shortcut and no users. |
| `test_steam_shortcuts.py` | `test_artwork` |  | 0.3 s | Artwork. |
| `test_steam_shortcuts.py` | `test_artwork_without_the_icon` |  | 0.3 s | Artwork without the icon. |
| `test_steam_shortcuts.py` | `test_the_job_closes_steam_for_it` |  | 0.3 s | The job closes steam for it. |
| `test_stream.py` | `test_messages_match_reference` | 8 |  | Messages match reference. |
| `test_stream.py` | `test_console_messages_decode` |  |  | Console messages decode. |
| `test_stream.py` | `test_bad_protobuf_is_refused` |  |  | Bad protobuf is refused. |
| `test_stream.py` | `test_launch_spec_and_big_match_reference` | 3 |  | Launch spec and big match reference. |
| `test_stream.py` | `test_missing_native_core_says_what_to_do` |  |  | Missing native core says what to do. |
| `test_stream.py` | `test_a_core_without_decoder_is_noted` |  |  | A core without decoder is noted. |
| `test_stream.py` | `test_stream_connects_runs_and_closes` | 2 |  | Stream connects runs and closes. (Skipped here.) |
| `test_stream.py` | `test_controller_buttons_reach_the_console` |  |  | Controller buttons reach the console. (Skipped here.) |
| `test_stream.py` | `test_shoulders_right_stick_and_touchpad_reach_the_console` |  |  | Shoulders right stick and touchpad reach the console. (Skipped here.) |
| `test_stream.py` | `test_player_experiment_options` | 3 |  | Player experiment options. |
| `test_stream.py` | `test_player_experiment_marked_sends_the_second_controller_apart` |  |  | Player experiment marked sends the second controller apart. (Skipped here.) |
| `test_stream.py` | `test_player_experiment_packed_sends_two_states_in_one_packet` |  |  | Player experiment packed sends two states in one packet. (Skipped here.) |
| `test_stream.py` | `test_low_latency_opens_the_decoder_in_low_delay_mode` |  |  | Low latency opens the decoder in low delay mode. (Skipped here.) |
| `test_stream.py` | `test_rumble_and_pad_info_go_to_the_controllers` |  |  | Rumble and pad info go to the controllers. (Skipped here.) |
| `test_stream.py` | `test_motion_reaches_the_console` |  |  | Motion reaches the console. (Skipped here.) |
| `test_stream.py` | `test_lost_units_come_from_fec` |  |  | Lost units come from fec. (Skipped here.) |
| `test_stream.py` | `test_lost_frames_are_reported_to_the_console_and_a_key_frame_asked_for` |  |  | Lost frames are reported to the console and a key frame asked for. (Skipped here.) |
| `test_stream.py` | `test_late_and_lost_video_packets_are_counted_apart` |  |  | Late and lost video packets are counted apart. (Skipped here.) |
| `test_stream.py` | `test_simulated_loss_drops_video_packets_on_purpose` |  |  | Simulated loss drops video packets on purpose. (Skipped here.) |
| `test_stream.py` | `test_streaminfo_before_bang_is_kept` |  |  | Streaminfo before bang is kept. (Skipped here.) |
| `test_stream.py` | `test_wrong_signature_is_only_noted` |  |  | Wrong signature is only noted. (Skipped here.) |
| `test_stream.py` | `test_big_split_over_packets` |  |  | Big split over packets. (Skipped here.) |
| `test_stream.py` | `test_console_refuses_the_version` |  |  | Console refuses the version. (Skipped here.) |
| `test_stream.py` | `test_console_ends_the_stream` |  |  | Console ends the stream. (Skipped here.) |
| `test_stream.py` | `test_no_answer_on_the_stream_port` |  |  | No answer on the stream port. (Skipped here.) |
| `test_stream.py` | `test_stream_job_runs_session_and_stream` |  |  | jobs.test_stream end to end: the control connection (fake_console.py) and the stream (fake_stream.py). (Skipped here.) |
| `test_stream_options.py` | `test_defaults_are_the_presets` |  |  | Defaults are the presets. |
| `test_stream_options.py` | `test_chosen_values_and_the_ps4_limit` |  |  | Chosen values and the ps4 limit. |
| `test_stream_options.py` | `test_json_keeps_what_is_valid` |  |  | Json keeps what is valid. |
| `test_stream_options.py` | `test_kept_with_the_console` |  |  | Kept with the console. |
| `test_stream_options.py` | `test_the_stream_asks_for_the_settings` |  |  | The stream asks for the settings. |
| `test_stream_options.py` | `test_dialog_shows_and_returns_the_settings` |  |  | Dialog shows and returns the settings. |
| `test_stream_stats.py` | `test_new_files_by_time_and_only_the_newest_kept` |  |  | New files by time and only the newest kept. |
| `test_stream_stats.py` | `test_folder_follows_xdg_state_home` |  |  | Folder follows xdg state home. |
| `test_stream_stats.py` | `test_processor_figures` |  |  | Processor figures. |
| `test_stream_stats.py` | `test_disk_figures_and_line` |  |  | Disk figures and line. |
| `test_stream_stats.py` | `test_processor_line` |  |  | Processor line. |
| `test_stream_stats.py` | `test_the_line_per_second` |  |  | The line per second. |
| `test_stream_stats.py` | `test_recorder_writes_a_header_and_a_line_per_second` |  |  | Recorder writes a header and a line per second. |
| `test_stream_view.py` | `test_colours_planes_and_orientation` | 2 |  | Colours planes and orientation. |
| `test_stream_view.py` | `test_full_range_bt601` |  |  | Full range bt601. |
| `test_stream_view.py` | `test_wide_picture_is_letterboxed` |  |  | Wide picture is letterboxed. |
| `test_stream_view.py` | `test_letterbox_arithmetic` |  |  | Letterbox arithmetic. |
| `test_stream_view.py` | `test_window_takes_pictures_and_ends_the_stream_on_close` |  |  | Window takes pictures and ends the stream on close. |
| `test_stream_view.py` | `test_pointer_hides_over_a_still_picture_and_comes_back_when_moved` |  |  | Pointer hides over a still picture and comes back when moved. |
| `test_video.py` | `test_planes_of_both_formats` |  |  | Planes of both formats. |
| `test_video.py` | `test_wrong_sizes_and_formats_are_refused` |  |  | Wrong sizes and formats are refused. |
| `test_video.py` | `test_matrix_follows_the_stream_or_the_size` |  |  | Matrix follows the stream or the size. |
| `test_video.py` | `test_limited_range_black_white_and_grey` | 3 |  | Limited range black white and grey. |
| `test_video.py` | `test_primaries_of_bt709` |  |  | Primaries of bt709. |
| `test_video.py` | `test_slot_keeps_only_the_newest` |  |  | Slot keeps only the newest. |

## apps/rpcs3

114 tests in 12 files, 5.6 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_controllers.py` | `test_the_controllers_connected` |  |  | The controllers connected. |
| `test_controllers.py` | `test_the_controllers_as_sdl_names_them` |  | 0.2 s | The names come from SDL3 itself, in a process of the app's own Python: one a line, in SDL's order; None when SDL3 is not there (the probe exits 3), when Python fails or when it does not answer in time. |
| `test_emulator.py` | `test_the_pin_points_at_the_build` |  |  | The pin points at the build. |
| `test_emulator.py` | `test_install_and_remove` |  |  | Install and remove. |
| `test_emulator.py` | `test_an_older_version_is_replaced` |  |  | An older version is replaced. |
| `test_emulator.py` | `test_rpcs3_updated_itself` |  |  | RPCS3's own update writes another build over the AppImage it runs from, in the same folder. |
| `test_emulator.py` | `test_a_different_file_is_refused` |  |  | A different file is refused. |
| `test_emulator.py` | `test_a_failed_install_keeps_the_installed_one` |  |  | A failed install keeps the installed one. |
| `test_emulator.py` | `test_download_errors_say_what_happened` |  |  | Download errors say what happened. |
| `test_emulator.py` | `test_a_newer_rpcs3_landmark` |  |  | A newer rpcs3 landmark. |
| `test_games.py` | `test_param_sfo_is_read` |  |  | Param sfo is read. |
| `test_games.py` | `test_a_disc_game_and_an_installed_game` |  |  | A disc game and an installed game. |
| `test_games.py` | `test_a_title_with_line_breaks` |  |  | A title with line breaks. |
| `test_games.py` | `test_updates_and_unfinished_folders_are_not_games` |  |  | Updates and unfinished folders are not games. |
| `test_games.py` | `test_the_installed_games_and_those_rpcs3_knows` |  |  | The installed games and those rpcs3 knows. |
| `test_games.py` | `test_scan_finds_games_sorted_once_and_not_too_deep` |  |  | Scan finds games sorted once and not too deep. |
| `test_games.py` | `test_a_disc_game_needs_its_ps3_disc_sfb` |  |  | A disc game needs its ps3 disc sfb. |
| `test_games.py` | `test_the_games_own_pictures` |  | 0.1 s | The games own pictures. |
| `test_games.py` | `test_a_failing_card_ends_no_scan` |  | 0.1 s | A failing card ends no scan. |
| `test_library.py` | `test_fixed_folders_and_the_firmware_file` |  |  | Fixed folders and the firmware file. |
| `test_library.py` | `test_removal_rows` |  |  | Removal rows. |
| `test_main_window.py` | `test_before_installing` |  | 0.1 s | Before installing. |
| `test_main_window.py` | `test_installed_with_firmware_and_games` |  |  | Installed with firmware and games. |
| `test_main_window.py` | `test_rpcs3_is_set_up_once_installed` |  | 0.1 s | Before RPCS3 is installed nothing is written; then its GUI settings get what the app owns (its welcome dialog and its update check off) and, with a controller connected, player 1 goes on it as SDL names it. |
| `test_main_window.py` | `test_without_sdl3_the_kernels_names_are_used` |  |  | Without sdl3 the kernels names are used. |
| `test_main_window.py` | `test_packages_installed_through_rpcs3_without_its_window` |  | 0.1 s | Games Install runs RPCS3 headless once per file (--headless --installpkg; owner, 24-10-2026): the licenses first, then the packages, the updates last (a fake RPCS3 that writes RPCS3's log lines and the files RPCS3 would); the result comes from RPCS3's log and the state follows. |
| `test_main_window.py` | `test_what_an_install_says` |  |  | The message after an install: RPCS3's log first, the files that came when the log says nothing. |
| `test_main_window.py` | `test_bazzites_volume_for_rpcs3` |  |  | The volume Bazzite remembers for RPCS3 (WirePlumber's stream-properties): in the Settings tab's Sound box, and said once while RPCS3 is muted there (found on the board, 24-10-2026). |
| `test_main_window.py` | `test_each_games_screen` |  |  | The Screen setting column: 16:9 (RPCS3's default), 4:3 or Fill screen, kept in the game's own settings in RPCS3 (custom_configs); a file RPCS3 wrote keeps its other lines; nothing is written while RPCS3 runs. |
| `test_main_window.py` | `test_the_settings_tab_follows_rpcs3s_file` |  |  | The settings tab follows rpcs3s file. |
| `test_main_window.py` | `test_the_steam_link` |  |  | The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the boxes, Screen setting and Start game do, and Steam in it is a link the app opens itself (Steam starts when it does not run). |
| `test_main_window.py` | `test_the_controller_state` |  |  | Beside the title: whether a controller is connected, from the kernel's list, looked at again every few seconds (owner, 24-10-2026: a controller switched off by its idle timer left a game without one). |
| `test_main_window.py` | `test_the_play_time_in_the_header` |  |  | The time spent in all games together, as RPCS3 counts it in persistent_settings.dat (milliseconds per serial), with each game in the tip; a dash while there is none. |
| `test_main_window.py` | `test_rpcs3_updated_itself` |  |  | Rpcs3 updated itself. |
| `test_main_window.py` | `test_the_apps_own_game_folders` |  |  | The disc games are put in Games/PS3 in the home folder, made with its Firmware folder when the app opens, and in Games/PS3 on a removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); no folder is chosen or remembered any more. |
| `test_main_window.py` | `test_the_firmware_is_taken_from_the_apps_folder` |  | 0.1 s | A PUP put in Games/PS3/Firmware is given to RPCS3 by itself once RPCS3 is installed (owner, 03-11-2026): once per file as it is, not while RPCS3 runs, and not when its version is installed already. |
| `test_main_window.py` | `test_a_disc_game_rpcs3_cannot_start` |  |  | A disc game rpcs3 cannot start. |
| `test_main_window.py` | `test_install_runs_off_the_window` |  | 0.1 s | Install runs off the window. |
| `test_main_window.py` | `test_the_firmware_installed_through_rpcs3_without_its_window` |  | 0.1 s | --headless --installfw (owner, 11-11-2026: RPCS3's window and its Success! |
| `test_main_window.py` | `test_rpcs3s_window` |  |  | RPCS3 settings opens RPCS3's own window through the run wrapper, for what the app does not set yet. |
| `test_main_window.py` | `test_steam_added_and_taken_out` |  | 0.3 s | Steam added and taken out. |
| `test_main_window.py` | `test_a_shortcut_named_before_the_system_prefix_is_renamed` |  | 0.2 s | A shortcut named by the title alone, as before "[PS3] ": Update Steam is on for it and renames it, with its play time; the artwork under its old number goes. |
| `test_main_window.py` | `test_a_shortcut_of_a_game_no_longer_found_is_taken_out` |  |  | A shortcut of a game no longer found is taken out. |
| `test_main_window.py` | `test_no_steam_game_mode_or_no_wrapper` |  | 0.1 s | No steam game mode or no wrapper. |
| `test_main_window.py` | `test_the_blue_look` |  | 0.1 s | The blue look. |
| `test_main_window.py` | `test_a_newer_rpcs3_is_mentioned` |  | 0.1 s | A newer rpcs3 is mentioned. |
| `test_main_window.py` | `test_the_log_tab` |  |  | What the window says goes to the Log tab with the time, after what the log file held already. |
| `test_main_window.py` | `test_clear_logs_empties_the_log` |  |  | Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones beside it removed and the Log tab emptied with them, the open page kept. |
| `test_main_window.py` | `test_the_blueprint_layout` |  |  | The managers' design (owner, 18-11-2026, PPSSPP Manager's): the window 900 wide when it opens, which is also its narrowest, and what is in it asks for no more; Play time the last pill of the second row; the six tabs share the whole width, the last one up to the margin, with no line over them; under the header's pills the two links alone, in the type of a pill's caption, each still a link. |
| `test_main_window.py` | `test_rpcn_off_online_offline` |  |  | RPCN (owner, 18-11-2026: as shadPS4 Manager's shadNet): the Account pill, the RPCN line with the name that signs in, and beside the app's state RPCN Off, Online when the server answers (asked, not signed in) or Offline. |
| `test_main_window.py` | `test_rpcn_from_rpcs3_while_it_runs` |  |  | While RPCS3 runs its log says whether it signed in; the server is not asked then. |
| `test_main_window.py` | `test_rpcn_set_up_from_the_window` |  |  | Rpcn set up from the window. |
| `test_main_window.py` | `test_covers_with_the_suites_key` |  | 0.5 s | Steam artwork… keeps the suite's key; Update Steam then looks up the games and puts the cover on the portrait, and a game in Steam not looked up yet makes the button do something again. |
| `test_main_window.py` | `test_another_build_installed_than_the_app_brings` |  |  | The RPCS3 line shows the state alone (owner, 07-11-2026), the box the installed version's landmark (owner, 24-10-2026: the box is not wide enough for the build), the advice in the tooltip and the log. |
| `test_main_window.py` | `test_the_settings_tab_is_not_squeezed_under_the_introduction` |  | 0.1 s | The introduction wraps to several lines and the state lines may too; their minimum heights count, so the tabs below get their minimum and the Sound box's rows keep their height (owner, 24-10-2026: squeezed unreadable on the board). |
| `test_main_window.py` | `test_unmute_bazzites_volume` |  | 0.1 s | Unmute beside Bazzite's volume (owner, 24-10-2026): shown while RPCS3 is muted there only; a click runs core's unmute off the window and the row follows what WirePlumber stored; a failure is said in red. |
| `test_main_window.py` | `test_remove_game_asks_what_to_keep` |  | 0.1 s | Remove game… (owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked deletes the rows still ticked off the window's thread and says what went and what stayed. |
| `test_main_window.py` | `test_start_game_starts_the_chosen_game_through_steam` |  | 0.2 s | The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your games through Steam, by its shortcut's number, and the open tab stays open. |
| `test_rpcn.py` | `test_the_password_as_rpcs3_derives_it` |  |  | The password as rpcs3 derives it. |
| `test_rpcn.py` | `test_create_an_account` |  |  | Create an account. |
| `test_rpcn.py` | `test_the_server_refuses_an_account` |  |  | The server refuses an account. |
| `test_rpcn.py` | `test_try_a_sign_in` |  |  | Try a sign in. |
| `test_rpcn.py` | `test_the_token_asked_for_again` |  |  | The token asked for again. |
| `test_rpcn.py` | `test_not_rpcn_another_version_or_no_server` |  |  | Not rpcn another version or no server. |
| `test_rpcn.py` | `test_a_packet_as_rpcs3_builds_it` |  |  | A packet as rpcs3 builds it. |
| `test_rpcn.py` | `test_server_address_name_and_token` |  |  | Server address name and token. |
| `test_rpcn.py` | `test_the_account_in_rpcs3s_own_files` |  |  | The account in rpcs3s own files. |
| `test_rpcn.py` | `test_what_rpcs3s_log_says_of_its_session` |  |  | What rpcs3s log says of its session. |
| `test_rpcn.py` | `test_the_account_window` |  |  | RPCN Account: the account as RPCS3 has it, a sign-in tried with the kept password, an account created with the typed one (derived, never as typed), and Save into RPCS3's own files, not while RPCS3 runs. |
| `test_rpcs3_settings.py` | `test_the_defaults_without_a_file` |  |  | The defaults without a file. |
| `test_rpcs3_settings.py` | `test_a_line_written_and_the_rest_kept` |  |  | A line written and the rest kept. |
| `test_rpcs3_settings.py` | `test_every_setting_is_one_of_rpcs3s` |  |  | The keys, sections and defaults as RPCS3 0.0.43 writes them (system_config.h); a CHOICE's default is one of its choices. |
| `test_run_wrapper.py` | `test_started_by_steam_with_a_real_controller` |  |  | Started by steam with a real controller. |
| `test_run_wrapper.py` | `test_started_by_steam_with_only_steams_controller` |  |  | Started by steam with only steams controller. |
| `test_run_wrapper.py` | `test_started_outside_steam` |  |  | Started outside steam. |
| `test_run_wrapper.py` | `test_started_by_steam_on_a_wayland_desktop` |  |  | Started by steam on a wayland desktop. |
| `test_run_wrapper.py` | `test_without_fusermount_it_unpacks_itself` |  |  | Without fusermount it unpacks itself. |
| `test_run_wrapper.py` | `test_the_game_started_goes_to_the_apps_log` |  |  | One line in the app's log file, in its form, with the game's folder name (the disc's, or the installed game's ID; not its path) and from where; a start without a game (RPCS3's window, the firmware, the packages) says nothing. |
| `test_run_wrapper.py` | `test_not_installed` |  |  | Not installed. |
| `test_run_wrapper.py` | `test_a_game_that_is_gone_is_not_started` |  |  | A shortcut to a game renamed, moved or deleted (owner, 03-11-2026): the emulator is not started, the wrapper says so and ends with 1, so Steam sees the game end; without the app's Python, the words go to stderr alone. |
| `test_saves.py` | `test_the_saves_are_read_from_their_folders` |  |  | The saves are read from their folders. |
| `test_saves.py` | `test_export_and_import_again` |  |  | Export and import again. |
| `test_saves.py` | `test_a_zip_with_the_files_at_the_top_takes_its_own_name` |  |  | A zip with the files at the top takes its own name. |
| `test_saves.py` | `test_what_is_no_save_is_refused` |  |  | What is no save is refused. |
| `test_saves.py` | `test_delete` |  |  | Delete. |
| `test_saves.py` | `test_the_tab_lists_the_saves_with_the_picture` |  |  | The tab lists the saves with the picture. |
| `test_saves.py` | `test_the_tab_exports_imports_and_deletes` |  |  | The tab exports imports and deletes. |
| `test_saves.py` | `test_nothing_is_changed_while_rpcs3_runs` |  |  | Nothing is changed while rpcs3 runs. |
| `test_settings_page.py` | `test_the_defaults_and_a_change` |  |  | The defaults and a change. |
| `test_settings_page.py` | `test_a_value_the_app_does_not_know_is_shown_as_it_is` |  |  | A value the app does not know is shown as it is. |
| `test_settings_page.py` | `test_nothing_written_while_rpcs3_runs` |  |  | Nothing written while rpcs3 runs. |
| `test_settings_page.py` | `test_bazzites_volume_for_rpcs3` |  |  | The Sound box's last row: the volume Bazzite remembers for RPCS3, as the window passes it; muted or turned down to nothing is a problem, said in words. |
| `test_settings_page.py` | `test_every_setting_has_a_widget_of_its_kind` |  |  | Every setting has a widget of its kind. |
| `test_shortcuts.py` | `test_the_launch_line_and_whose_shortcut_it_is` |  |  | The launch line and whose shortcut it is. |
| `test_shortcuts.py` | `test_names_are_unique` |  |  | Names are unique. |
| `test_shortcuts.py` | `test_add_then_take_out` |  | 0.4 s | Add then take out. |
| `test_shortcuts.py` | `test_a_shortcut_taken_out_under_the_name_it_has` |  |  | A shortcut taken out under the name it has. |
| `test_shortcuts.py` | `test_artwork_sizes_with_and_without_the_games_pictures` |  | 0.7 s | Artwork sizes with and without the games pictures. |
| `test_shortcuts.py` | `test_pictures_from_steamgriddb_in_place_of_the_drawn_ones` |  | 0.7 s | Pictures from steamgriddb in place of the drawn ones. |
| `test_userdata.py` | `test_rpcs3s_folder_follows_xdg_config_home` |  |  | Rpcs3s folder follows xdg config home. |
| `test_userdata.py` | `test_vfs_yml_and_the_default_drives` |  |  | Vfs yml and the default drives. |
| `test_userdata.py` | `test_drives_moved_elsewhere` |  |  | Drives moved elsewhere. |
| `test_userdata.py` | `test_games_yml` |  |  | Games yml. |
| `test_userdata.py` | `test_the_firmware_version` |  |  | The firmware version. |
| `test_userdata.py` | `test_the_play_time_rpcs3_counted` |  |  | persistent_settings.dat: milliseconds per serial under [Playtime] (rounded up to whole seconds, as RPCS3 shows them), the last-played date under [LastPlayed] in RPCS3's ISO form or the older spelled-out ones. |
| `test_userdata.py` | `test_rpcs3s_gui_settings_get_what_the_app_owns` |  |  | No CurrentSettings.ini yet: the three keys in their sections. |
| `test_userdata.py` | `test_the_pad_file_for_player_1` |  |  | Player 1 on the first controller as SDL names it, with RPCS3's default SDL mapping; two controllers of one name are " 1" and " 2"; a pad file RPCS3 wrote is never touched, an empty one (RPCS3's keyboard fallback) is. |
| `test_userdata.py` | `test_a_games_screen_in_its_own_settings` |  |  | The screen choice in custom_configs/config_<serial>.yml: made from nothing, or two lines of a file RPCS3 wrote; read back, RPCS3's default without a file. |
| `test_userdata.py` | `test_packages_and_licenses_in_a_folder` |  |  | The folder's own files, by name, as RPCS3 takes them from a folder: not a subfolder's. |
| `test_userdata.py` | `test_a_packages_header` |  |  | The unencrypted header and metadata of a PKG file (the first 288 bytes of the owner's three Lumines Supernova packages): the content ID, and the PATCH flag that marks the game's update. |
| `test_userdata.py` | `test_what_rpcs3s_log_says_of_an_install` |  |  | The install lines RPCS3's main window writes to its log, read back; two runs' reports added up. |
| `test_userdata.py` | `test_what_rpcs3s_log_says_of_a_firmware_install` |  |  | The lines HandlePupInstallation writes, from a headless --installfw (owner, 11-11-2026). |
| `test_userdata.py` | `test_whether_rpcs3_runs` |  |  | RPCS3's process is rpcs3, or AppRun.wrapped running rpcs3 (the AppImage's link); a zombie does not count. |
| `test_userdata.py` | `test_the_version_a_pup_holds` |  |  | pup_version reads file 0x100 of a PUP as RPCS3 does (owner, 03-11-2026); anything else gives "". |

## apps/sftp

86 tests in 11 files, 5.6 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_app_logging.py` | `test_logs_to_file` |  |  | Logs to file. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_app_logging.py` | `test_the_log_writes_the_users_folders_as_home` |  |  | No user name in the log (owner, 03-11-2026: the privacy rule): the home folder as ~ in every line. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_connect_ssh_uses_strict_host_key_checking` |  |  | Connect ssh uses strict host key checking. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_connect_ssh_compression_is_negotiated_by_connect_only` |  |  | Connect ssh compression is negotiated by connect only. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_unknown_host_policy_reports_identity_and_key` |  |  | Unknown host policy reports identity and key. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_save_trusted_host_key_adds_key_to_user_known_hosts` |  |  | Save trusted host key adds key to user known hosts. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_connect_ssh_rejects_invalid_parameters` |  |  | Connect ssh rejects invalid parameters. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_connect_ssh_closes_client_after_connection_failure` |  |  | Connect ssh closes client after connection failure. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_connect_ssh_retries_on_failure` |  |  | Connect ssh retries on failure. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_connect_ssh_does_not_retry_host_key_error` |  |  | Connect ssh does not retry host key error. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_server_action_uses_only_approved_command` |  |  | Server action uses only approved command. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_server_action_rejects_unrecognized_command` |  |  | Server action rejects unrecognized command. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_connection.py` | `test_server_action_reports_remote_errors` |  |  | Server action reports remote errors. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_iso_hms` |  |  | Test ISO date format with HH:MM:SS. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_iso_hm` |  |  | Test ISO date format with HH:MM. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_us_format` |  |  | Test US date format MM/DD/YYYY. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_eu_format` |  |  | Test EU date format DD/MM/YYYY. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_zero_timestamp` |  |  | Test that zero timestamp returns empty string. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_negative_timestamp` |  |  | Test that negative timestamp returns empty string. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_very_large_timestamp` |  |  | Test very large timestamps (far future). (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_all_format_combinations` |  |  | Test all combinations of date and time formats. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_datetime.py` | `test_format_datetime_consistency` |  |  | Test that the same timestamp always formats the same way. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_auto_mode_bytes` |  |  | Auto mode: bytes without separator. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_auto_mode_kilobytes` |  |  | Auto mode: kilobytes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_auto_mode_megabytes` |  |  | Auto mode: megabytes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_auto_mode_gigabytes` |  |  | Auto mode: gigabytes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_binary_mode` |  |  | Binary mode with KiB, MiB, GiB units. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_decimal_mode` |  |  | Decimal mode with KB, MB, GB units (1000-based). (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_with_thousands_separator` |  |  | Test thousands separator in all modes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_decimal_places` |  |  | Test different decimal place settings. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_zero` |  |  | Test zero size. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_negative` |  |  | Test negative size (should be treated as 0). (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_format_size.py` | `test_format_size_large_numbers` |  |  | Test very large file sizes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_local_host.py` | `test_status_reads_sshd_and_the_firewall` |  |  | Status reads sshd and the firewall. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_local_host.py` | `test_status_without_firewalld_or_openssh_server` |  |  | Status without firewalld or openssh server. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_local_host.py` | `test_install_hint_follows_ostree` |  |  | Install hint follows ostree. |
| `test_local_host.py` | `test_start_enables_sshd_and_opens_the_firewall_through_pkexec` |  |  | Start enables sshd and opens the firewall through pkexec. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_local_host.py` | `test_set_reads_the_state_again_or_says_why_it_failed` |  |  | Set reads the state again or says why it failed. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_local_host.py` | `test_the_tab_shows_the_local_state_and_its_button` |  |  | The tab shows the local state and its button. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_window_has_the_suite_header_and_shows_the_states` |  |  | Window has the suite header and shows the states. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_changed_settings_reach_the_queue_and_the_lists` |  |  | Changed settings reach the queue and the lists. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_server_status_updates_pill_and_toggle_button` |  |  | Server status updates pill and toggle button. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_unknown_server_status_disables_start_stop_button` |  |  | Unknown server status disables start stop button. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_unknown_host_prompt_only_saves_after_yes` |  |  | Unknown host prompt only saves after yes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_service_button_runs_action_matching_observed_state` |  |  | Service button runs action matching observed state. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_service_changes_require_consent` |  |  | Service changes require consent. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_server_status_after_action_runs_action_then_checks_state` |  |  | Server status after action runs action then checks state. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_worker_is_kept_alive_until_its_thread_finishes` |  |  | Worker is kept alive until its thread finishes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_error_dot_shows_after_an_error_and_goes_with_its_window` |  |  | Error dot shows after an error and goes with its window. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_local_list_keeps_every_cell_of_a_row_together` |  |  | Local list keeps every cell of a row together. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_upload_queues_every_selected_row_but_the_parent` |  |  | Upload queues every selected row but the parent. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_local_rows_drag_as_file_urls` |  |  | Local rows drag as file urls. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_files_dropped_on_the_remote_list_are_copied_while_connected` |  |  | Files dropped on the remote list are copied while connected. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_existing_targets_ask_once_when_the_answer_holds_for_the_rest` |  |  | Existing targets ask once when the answer holds for the rest. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_connect_is_a_pill_in_the_header` |  |  | Connect sits beside the states as a pill (owner, 26-10-2026): a click connects the SFTP Client, and the pill reads what the tab says (Connecting…, Disconnect) and cannot be clicked while it connects. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_the_password_rules_always_show_at_the_right` |  |  | In the SFTP Client the rules sit at the right of the form from the start, in muted text, and turn into what is missing (red) or a check (green) as a password is typed; the warning shows and hides as before. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_main_window.py` | `test_an_unsafe_password_is_advice_and_the_app_connects` |  |  | The password rules are advice: an unsafe password without a key gets one warning, and both tabs connect. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_profiles.py` | `test_profile_store_persists_connection_details_without_credentials` |  |  | Profile store persists connection details without credentials. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_profiles.py` | `test_saving_a_profile_replaces_the_existing_profile` |  |  | Saving a profile replaces the existing profile. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_profiles.py` | `test_profile_store_deletes_selected_profile` |  |  | Profile store deletes selected profile. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_profiles.py` | `test_profile_store_reports_malformed_profile_file` |  |  | Profile store reports malformed profile file. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_round_trip` |  |  | Round trip. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_missing_or_corrupt_gives_defaults` |  |  | Missing or corrupt gives defaults. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_invalid_rejected` |  |  | Invalid rejected. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_new_settings_validated` |  |  | New settings validated. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_keepalive_interval` |  |  | Keepalive interval. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_view_hidden_files` |  |  | View hidden files. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_size_format` |  |  | Size format. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_settings.py` | `test_sound_on_transfer_complete` |  |  | Sound on transfer complete. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_sshd_config.py` | `test_read` |  |  | Read. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_sshd_config.py` | `test_write_validates_and_adds_newline` |  |  | Write validates and adds newline. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_sshd_config.py` | `test_write_failure_raises` |  |  | Write failure raises. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_files_live_in_folders_named_after_the_app` |  |  | Files live in folders named after the app. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_settings_are_loaded_applied_and_kept` |  |  | Settings are loaded applied and kept. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_invalid_settings_are_refused_and_not_applied` |  |  | Invalid settings are refused and not applied. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_dialog_shows_a_settings_error_and_stays_open` |  |  | Dialog shows a settings error and stays open. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_password_requirements` |  |  | Password requirements. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_beep_plays_the_desktop_sound_through_paplay` |  |  | Beep plays the desktop sound through paplay. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_state.py` | `test_beep_falls_back_to_qt` |  |  | Beep falls back to qt. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_round_trip` |  |  | Round trip. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_progress_reports_bytes` |  |  | Progress reports bytes. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_skip_existing` |  |  | Skip existing. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_download_rejects_traversal` |  |  | Download rejects traversal. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_delete_local_and_symlink` |  |  | Delete local and symlink. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_delete_remote_tree` |  |  | Delete remote tree. (Not run here: it needs the built native module, which CI's native job tests.) |
| `test_transfers.py` | `test_sanitize_filename` |  |  | Sanitize filename. (Not run here: it needs the built native module, which CI's native job tests.) |

## apps/shadps4

147 tests in 17 files, 7.7 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_cli.py` | `test_open_reads_header_and_sfo` |  |  | Open reads header and sfo. |
| `test_cli.py` | `test_full_extraction` |  |  | Full extraction. |
| `test_cli.py` | `test_cli_extracts_into_title_id_folder` |  |  | Cli extracts into title id folder. |
| `test_cli.py` | `test_version_is_the_apps` |  |  | Version is the apps. |
| `test_cli.py` | `test_cli_rejects_non_pkg` |  |  | Cli rejects non pkg. |
| `test_compare.py` | `test_run_compare_counts_and_report` |  |  | Run compare counts and report. |
| `test_compare.py` | `test_run_compare_without_hash_ignores_content` |  |  | Run compare without hash ignores content. |
| `test_compare.py` | `test_compare_main_rejects_missing_folder` |  |  | Compare main rejects missing folder. |
| `test_compare.py` | `test_summarize_delta` |  |  | Summarize delta. |
| `test_compare.py` | `test_compare_delta_main_writes_out` |  |  | Compare delta main writes out. |
| `test_compare.py` | `test_window_compare_report_delta` |  |  | Window compare report delta. |
| `test_compare.py` | `test_window_compare_report_delta_cancel` |  |  | Window compare report delta cancel. |
| `test_controllers.py` | `test_the_controllers_connected` |  |  | The controllers connected. |
| `test_crypto.py` | `test_decrypt_pfs_matches_reference_implementation` |  |  | Decrypt pfs matches reference implementation. |
| `test_crypto.py` | `test_aes_cbc_decrypt_copies_partial_tail` |  |  | Aes cbc decrypt copies partial tail. |
| `test_crypto.py` | `test_pfs_gen_crypto_key_layout` |  |  | Pfs gen crypto key layout. |
| `test_crypto.py` | `test_rsa_pkcs1v15_roundtrip` | 2 |  | Rsa pkcs1v15 roundtrip. |
| `test_crypto.py` | `test_rsa_invalid_padding_returns_none` |  |  | Rsa invalid padding returns none. |
| `test_emulator.py` | `test_the_pin_points_at_the_release` |  |  | The pin points at the release. |
| `test_emulator.py` | `test_install_and_remove` |  |  | Install and remove. |
| `test_emulator.py` | `test_an_older_version_is_replaced` |  |  | An older version is replaced. |
| `test_emulator.py` | `test_a_different_file_is_refused` |  |  | A different file is refused. |
| `test_emulator.py` | `test_a_zip_without_the_appimage_or_damaged` |  |  | A zip without the appimage or damaged. |
| `test_emulator.py` | `test_download_errors_say_what_happened` |  |  | Download errors say what happened. |
| `test_emulator.py` | `test_a_newer_shadps4_release` |  |  | A newer shadps4 release. |
| `test_extract.py` | `test_a_package_says_what_it_is` |  |  | A package says what it is. |
| `test_extract.py` | `test_a_game_is_unpacked_into_its_ids_folder` |  |  | A game is unpacked into its ids folder. |
| `test_extract.py` | `test_an_update_goes_beside_its_game_and_is_replaced_only_when_asked` |  | 0.1 s | An update goes beside its game and is replaced only when asked. |
| `test_extract.py` | `test_files_that_fail_are_counted_and_named` |  |  | Files that fail are counted and named. |
| `test_extract.py` | `test_the_packages_waiting_in_the_game_folders` |  |  | The packages dropped in the game folders (owner, 30-10-2026: the manager takes care of them): a game whose title ID is not unpacked, an update its game lacks (that version), the games first; no add-on, no file that is no package. |
| `test_extract.py` | `test_a_package_is_placed_beside_itself_an_update_beside_its_game` |  | 0.1 s | A package is placed beside itself an update beside its game. |
| `test_extract_dialog.py` | `test_preview_shows_sfo_and_icon` |  |  | Preview shows sfo and icon. |
| `test_extract_dialog.py` | `test_package_given_when_it_opens_or_later` |  |  | Package given when it opens or later. |
| `test_extract_dialog.py` | `test_extract_guardrail_and_preview_only` |  | 0.1 s | Extract guardrail and preview only. |
| `test_extract_dialog.py` | `test_an_update_goes_beside_its_game` |  | 0.3 s | An update goes beside its game. |
| `test_extract_dialog.py` | `test_preview_only_is_no_extraction` |  |  | Preview only is no extraction. |
| `test_extract_dialog.py` | `test_salvage_mode_is_passed_to_the_worker` |  | 0.1 s | Salvage mode is passed to the worker. |
| `test_extract_dialog.py` | `test_rename_to_content_id` |  |  | Rename to content id. |
| `test_extract_dialog.py` | `test_right_click_on_the_icon_offers_the_menu` |  |  | Right click on the icon offers the menu. |
| `test_extract_dialog.py` | `test_empty_inputs_warn_instead_of_starting` |  |  | Empty inputs warn instead of starting. |
| `test_extract_dialog.py` | `test_the_output_is_a_game_folder` |  |  | No folder used before: the first game folder; the note says whether the game will show up. |
| `test_extract_dialog.py` | `test_the_last_output_folder_comes_first` |  |  | The last output folder comes first. |
| `test_extract_dialog.py` | `test_another_apps_folders_are_not_adopted` |  |  | Another apps folders are not adopted. |
| `test_extract_dialog.py` | `test_no_closing_while_it_extracts` |  | 0.1 s | Its thread would be destroyed under it: Esc does nothing, closing says to wait. |
| `test_extract_dialog.py` | `test_the_crash_marker_lives_while_it_is_open` |  |  | The crash marker lives while it is open. |
| `test_extract_dialog.py` | `test_extract_pkg_is_games_install` |  | 0.1 s | Extract pkg is games install. |
| `test_extract_dialog.py` | `test_an_extracted_game_shows_up` |  | 0.1 s | Extract PKG on the game folders: the extraction into the first one, and the games found again after. |
| `test_extract_dialog.py` | `test_a_later_package_goes_into_the_open_window` |  |  | A later package goes into the open window. |
| `test_extract_dialog.py` | `test_a_package_dropped_on_the_window` |  |  | A package dropped on the window. |
| `test_extract_dialog.py` | `test_without_cryptography_it_says_what_to_do` |  |  | Without cryptography it says what to do. |
| `test_extract_dialog.py` | `test_several_packages_are_extracted_one_after_the_other` |  | 0.2 s | Browse (or a drop) with several packages: the first is loaded, the rest wait, games before updates, and Extract PKG runs through them into the same folder, the log running on. |
| `test_extract_dialog.py` | `test_packages_dropped_or_given_later_join_the_queue` |  |  | Packages dropped or given later join the queue. |
| `test_games.py` | `test_param_sfo_is_read` |  |  | Param sfo is read. |
| `test_games.py` | `test_a_game_from_its_param_sfo_or_its_folder` |  |  | A game from its param sfo or its folder. |
| `test_games.py` | `test_updates_mods_and_add_ons_are_not_games` |  |  | Updates mods and add ons are not games. |
| `test_games.py` | `test_scan_finds_games_sorted_once_and_not_too_deep` |  |  | Scan finds games sorted once and not too deep. |
| `test_games.py` | `test_an_update_beside_its_game_is_left_out` |  |  | An update beside its game is left out. |
| `test_games.py` | `test_a_game_with_its_update_in_it_is_a_game` |  |  | Dumped from a PS4 with the update installed: param.sfo says "gp", and there is no other game with its ID (LUMINES REMASTERED, CUSA11624, on the owner's board, 14-10-2026). |
| `test_games.py` | `test_the_games_own_pictures` |  | 0.1 s | The games own pictures. |
| `test_games.py` | `test_a_failing_card_ends_no_scan` |  | 0.1 s | A failing card ends no scan. |
| `test_library.py` | `test_fixed_folders` |  |  | Fixed folders. |
| `test_library.py` | `test_removal_rows` |  |  | Removal rows. |
| `test_main_window.py` | `test_before_installing` |  | 0.1 s | Before installing. |
| `test_main_window.py` | `test_installed_with_games` |  |  | Installed with games. |
| `test_main_window.py` | `test_system_modules_are_taken_from_the_apps_folder` |  |  | The .sprx files put in Games/PS4/Modules are copied into shadPS4's module folder when the window opens and on Refresh, only what is new or changed (owner, 03-11-2026); the state follows at once. |
| `test_main_window.py` | `test_install_runs_off_the_window` |  | 0.1 s | Install runs off the window. |
| `test_main_window.py` | `test_another_version_installed_than_the_app_brings` |  |  | The line shows the state alone (owner, 07-11-2026), the box the version, the advice in the tooltip and the log once (as RPCS3 Manager's); a nightly build from before the channel went is too long for the box. |
| `test_main_window.py` | `test_steam_added_and_taken_out` |  | 0.3 s | Steam added and taken out. |
| `test_main_window.py` | `test_a_shortcut_without_its_logo_is_brought_up_to_date` |  | 0.3 s | A shortcut made before the app set a logo: Update Steam is on for it until the logo is there. |
| `test_main_window.py` | `test_a_shortcut_with_the_tags_of_the_old_name_is_brought_up_to_date` |  | 0.2 s | A shortcut with older tags: Update Steam is on until it has the current tags. |
| `test_main_window.py` | `test_a_shortcut_named_before_the_system_prefix_is_renamed` |  | 0.2 s | A shortcut named by the title alone, as before "[PS4] ": Update Steam is on for it and renames it, with its play time; the artwork under its old number goes. |
| `test_main_window.py` | `test_a_shortcut_of_a_game_no_longer_found_is_taken_out` |  |  | A shortcut of a game no longer found is taken out. |
| `test_main_window.py` | `test_no_steam_game_mode_or_no_wrapper` |  | 0.1 s | No steam game mode or no wrapper. |
| `test_main_window.py` | `test_the_apps_own_game_folders` |  |  | The games are put in Games/PS4 in the home folder, made with its Modules folder when the app opens, and in Games/PS4 on a removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); shadPS4's own game folders (config.json) are made the same, so its own window lists the games too, not while it runs. |
| `test_main_window.py` | `test_the_settings_tab_follows_shadps4s_file` |  |  | The Settings tab reads config.json (shadPS4's defaults where a key is missing) and writes one key the moment it is changed, the rest of the file kept; not while shadPS4 runs. |
| `test_main_window.py` | `test_bazzites_volume_for_shadps4` |  |  | The volume Bazzite remembers for shadPS4 (WirePlumber's stream-properties): in the Settings tab's Sound box, and said once while shadPS4 is muted there (as on the board, 24-10-2026). |
| `test_main_window.py` | `test_the_play_time_in_the_header` |  |  | The time spent in all games together, as shadPS4 counts it in play_time.txt (H:MM:SS and the last start per Id), with each game in the tip; a dash while there is none. |
| `test_main_window.py` | `test_the_controller_state` |  |  | Beside the title: whether a controller is connected, from the kernel's list, looked at again every few seconds (owner, 24-10-2026: a controller switched off by its idle timer left a game without one). |
| `test_main_window.py` | `test_the_quit_hotkeys_are_set_up_and_logged` |  |  | The quit hotkeys are set up and logged. |
| `test_main_window.py` | `test_the_steam_link` |  |  | The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the boxes and Start game do, and Steam in it is a link the app opens itself. |
| `test_main_window.py` | `test_shadps4s_window` |  |  | shadPS4 settings opens shadPS4's own window (Big Picture) through the run wrapper. |
| `test_main_window.py` | `test_the_log_tab` |  |  | What the window says goes to the Log tab with the time, after what the log file held already. |
| `test_main_window.py` | `test_clear_logs_empties_the_log` |  |  | Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones beside it removed and the Log tab emptied with them, the open page kept. |
| `test_main_window.py` | `test_the_blueprint_layout` |  |  | The managers' design (owner, 18-11-2026, PPSSPP Manager's): the window 900 wide when it opens, which is also its narrowest, and what is in it asks for no more; Play time the last pill of the second row; the six tabs share the whole width, the last one up to the margin, with no line over them; under the header's pills the two links alone, in the type of a pill's caption, each still a link. |
| `test_main_window.py` | `test_the_blue_look` |  | 0.1 s | The blue look. |
| `test_main_window.py` | `test_the_settings_tab_is_not_squeezed` |  |  | The introduction and the state lines may wrap; their minimum heights count, so the tabs below get their minimum and the Settings tab's rows keep their height (as RPCS3 Manager's). |
| `test_main_window.py` | `test_a_newer_shadps4_is_mentioned` |  | 0.1 s | A newer shadps4 is mentioned. |
| `test_main_window.py` | `test_shadnet_set_up_from_the_window` |  | 0.1 s | Shadnet set up from the window. |
| `test_main_window.py` | `test_shadnet_not_saved_while_shadps4_runs` |  |  | Shadnet not saved while shadps4 runs. |
| `test_main_window.py` | `test_shadnet_pill_off_online_offline` |  | 0.1 s | Shadnet pill off online offline. |
| `test_main_window.py` | `test_shadnet_pill_from_shadps4_while_it_runs` |  |  | Shadnet pill from shadps4 while it runs. |
| `test_main_window.py` | `test_covers_with_the_suites_key` |  | 0.5 s | Steam artwork… keeps the suite's key; Update Steam then looks up the games and puts the cover on the portrait, and a game in Steam not looked up yet makes the button do something again. |
| `test_main_window.py` | `test_unmute_bazzites_volume` |  | 0.1 s | Unmute beside Bazzite's volume (owner, 24-10-2026): shown while shadPS4 is muted there only; a click runs core's unmute off the window and the row follows what WirePlumber stored; a failure is said in red. |
| `test_main_window.py` | `test_remove_game_asks_what_to_keep` |  | 0.1 s | Remove game… (owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked deletes the rows still ticked off the window's thread and says what went and what stayed. |
| `test_main_window.py` | `test_remove_game_on_a_package_row_offers_the_package` |  | 0.1 s | Remove game… on a PKG row (owner, 11-11-2026: a package that cannot be unpacked stayed a row with no way out): the keep window offers the .pkg file; Cancel keeps it, Delete marked deletes it and the row goes. |
| `test_main_window.py` | `test_packages_in_a_game_folder_wait_as_rows_and_unpack_all_takes_the_game_first` |  | 0.2 s | A .pkg put in a game folder (owner, 05-11-2026): a row of its own, PKG or PKG update, after the games; an update whose game still waits says so; Unpack all unpacks the game first and its update beside it, then the keep window offers the packages: kept ones are no longer rows, deleted ones are gone. |
| `test_main_window.py` | `test_start_game_starts_the_chosen_game_through_steam` |  | 0.2 s | The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your games through Steam, by its shortcut's number, and the open tab stays open. |
| `test_pkg.py` | `test_sanitize_file_name` |  |  | Sanitize file name. |
| `test_pkg.py` | `test_find_pfsc_offset_priorities` |  |  | Find pfsc offset priorities. |
| `test_pkg.py` | `test_decompress_pfsc_roundtrip` |  |  | Decompress pfsc roundtrip. |
| `test_pkg.py` | `test_pkg_header_parse_offsets` |  |  | Pkg header parse offsets. |
| `test_psf.py` | `test_psf_parse` |  |  | Psf parse. |
| `test_psf.py` | `test_psf_rejects_garbage` |  |  | Psf rejects garbage. |
| `test_run_wrapper.py` | `test_started_by_steam_with_a_real_controller` |  |  | Started by steam with a real controller. |
| `test_run_wrapper.py` | `test_started_by_steam_with_only_steams_controller` |  |  | Started by steam with only steams controller. |
| `test_run_wrapper.py` | `test_started_outside_steam` |  |  | Started outside steam. |
| `test_run_wrapper.py` | `test_started_by_steam_on_a_wayland_desktop` |  |  | Started by steam on a wayland desktop. |
| `test_run_wrapper.py` | `test_the_game_started_goes_to_the_apps_log` |  |  | One line in the app's log file, in its form, with the game's folder name (its ID as Extract PKG names it; not its path) and from where; a start without a game (shadPS4's own window) says nothing. |
| `test_run_wrapper.py` | `test_a_game_that_is_gone_is_not_started` |  |  | A shortcut to a game renamed, moved or deleted (owner, 03-11-2026): the emulator is not started, the wrapper says so and ends with 1, so Steam sees the game end; without the app's Python, the words go to stderr alone. |
| `test_saves.py` | `test_the_saves_are_read_from_their_folders` |  |  | The saves are read from their folders. |
| `test_saves.py` | `test_export_and_import_again` |  |  | Export and import again. |
| `test_saves.py` | `test_what_is_no_save_is_refused` |  |  | What is no save is refused. |
| `test_saves.py` | `test_delete_takes_the_games_folder_with_its_last_save` |  |  | Delete takes the games folder with its last save. |
| `test_saves.py` | `test_the_tab_lists_the_saves_under_their_games` |  |  | The tab lists the saves under their games. |
| `test_saves.py` | `test_the_tab_exports_imports_and_deletes` |  |  | The tab exports imports and deletes. |
| `test_saves.py` | `test_nothing_is_changed_while_shadps4_runs` |  |  | Nothing is changed while shadps4 runs. |
| `test_shadnet.py` | `test_create_an_account` |  |  | Create an account. |
| `test_shadnet.py` | `test_the_server_refuses_an_account` | 4 |  | The server refuses an account. |
| `test_shadnet.py` | `test_try_a_sign_in` |  |  | Try a sign in. |
| `test_shadnet.py` | `test_not_shadnet_another_version_or_no_server` |  |  | Not shadnet another version or no server. |
| `test_shadnet.py` | `test_a_packet_as_shadps4_builds_it` |  |  | A packet as shadps4 builds it. |
| `test_shadnet.py` | `test_server_address_and_name` |  |  | Server address and name. |
| `test_shadnet.py` | `test_the_server_answers_without_a_sign_in` |  |  | The server answers without a sign in. |
| `test_shadnet.py` | `test_shadps4s_session_from_its_newest_log` |  |  | Shadps4s session from its newest log. |
| `test_shortcuts.py` | `test_the_launch_line_and_whose_shortcut_it_is` |  |  | The launch line and whose shortcut it is. |
| `test_shortcuts.py` | `test_names_are_unique` |  |  | Names are unique. |
| `test_shortcuts.py` | `test_add_then_take_out` |  | 0.5 s | Add then take out. |
| `test_shortcuts.py` | `test_a_shortcut_taken_out_under_the_name_it_has` |  |  | A shortcut taken out under the name it has. |
| `test_shortcuts.py` | `test_artwork_sizes_with_and_without_the_games_pictures` |  | 0.7 s | Artwork sizes with and without the games pictures. |
| `test_shortcuts.py` | `test_pictures_from_steamgriddb_in_place_of_the_drawn_ones` |  | 0.7 s | Pictures from steamgriddb in place of the drawn ones. |
| `test_shortcuts.py` | `test_a_shortcut_made_without_a_logo` |  | 0.3 s | A shortcut made without a logo. |
| `test_shortcuts.py` | `test_a_shortcut_with_the_tags_of_the_old_name` |  |  | A shortcut with the tags of the old name. |
| `test_userdata.py` | `test_game_folders_and_module_folder` |  |  | Game folders and module folder. |
| `test_userdata.py` | `test_a_config_that_is_not_what_was_expected` |  |  | A config that is not what was expected. |
| `test_userdata.py` | `test_modules` |  |  | Modules. |
| `test_userdata.py` | `test_the_users_and_shadnet` |  |  | The users and shadnet. |
| `test_userdata.py` | `test_saving_shadnet_changes_only_its_settings` |  |  | Saving shadnet changes only its settings. |
| `test_userdata.py` | `test_saving_shadnet_before_shadps4_ran_or_for_no_user` |  |  | Saving shadnet before shadps4 ran or for no user. |
| `test_userdata.py` | `test_shadnet_in_the_network_section` |  |  | shadPS4 0.20.0 keeps shadNet's settings in Network and takes them from General only while Network does not have them; once it saved its config, General has none. |
| `test_userdata.py` | `test_whether_shadps4_runs` |  |  | Whether shadps4 runs. |
| `test_userdata.py` | `test_the_quit_hotkeys` |  |  | The quit hotkeys. |
| `test_userdata.py` | `test_one_setting_written_the_rest_kept` |  |  | write_config sets one key as shadPS4 writes the file (indented by two, no newline at the end); a missing file is made, an unreadable one is never written over. |
| `test_userdata.py` | `test_a_game_folder_taken_out` |  |  | A game folder taken out. |
| `test_userdata.py` | `test_modules_copied_from_a_folder` |  |  | Modules copied from a folder. |
| `test_userdata.py` | `test_play_time_as_shadps4_writes_it` |  |  | play_time.txt as shadPS4 0.20.0 writes it, from the owner's board (24-10-2026). |
| `test_userdata.py` | `test_sync_modules_copies_what_is_new_or_changed` |  |  | The modules put in Games/PS4/Modules go into shadPS4's folder once (owner, 03-11-2026); a changed one again. |
| `test_userdata.py` | `test_set_game_folders_writes_install_dirs` |  |  | Set game folders writes install dirs. |

## apps/ssd

50 tests in 4 files, 0.8 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_main_window.py` | `test_version_is_the_single_source` |  |  | Version is the single source. |
| `test_main_window.py` | `test_icons_are_beside_the_package` |  |  | Icons are beside the package. |
| `test_main_window.py` | `test_the_boards_drive_in_the_header` |  | 0.1 s | The boards drive in the header. |
| `test_main_window.py` | `test_several_drives_are_chosen_from_the_list_and_kept_on_refresh` |  |  | Several drives are chosen from the list and kept on refresh. |
| `test_main_window.py` | `test_a_warning_turns_the_state_and_the_health_red` |  |  | A warning turns the state and the health red. |
| `test_main_window.py` | `test_partly_read_and_no_drive_and_no_udisks` |  |  | Partly read and no drive and no udisks. |
| `test_main_window.py` | `test_the_threaded_read_reports_back` |  |  | The threaded read reports back. |
| `test_main_window.py` | `test_the_specs_are_pills` |  |  | The specs are pills. |
| `test_main_window.py` | `test_the_serial_shows_in_a_popup_and_the_pill_keeps_its_width` |  |  | The serial shows in a popup and the pill keeps its width. |
| `test_main_window.py` | `test_a_usb_stick_shows_its_specs_without_smart` |  |  | A usb stick shows its specs without smart. |
| `test_main_window.py` | `test_an_available_firmware_turns_the_update_pill_orange` |  |  | An available firmware turns the update pill orange. |
| `test_main_window.py` | `test_a_reported_port_limit_below_the_drive_rating_is_orange` |  |  | A reported port limit below the drive rating is orange. |
| `test_main_window.py` | `test_a_reported_port_limit_above_the_drive_link_is_sufficient` |  |  | A reported port limit above the drive link is sufficient. |
| `test_main_window.py` | `test_measuring_shows_the_speeds_per_drive` |  |  | Measuring shows the speeds per drive. |
| `test_main_window.py` | `test_the_enclosure_on_a_slow_link_and_a_folder_of_roots` |  |  | The enclosure on a slow link and a folder of roots. |
| `test_main_window.py` | `test_screenshot_saves_the_window_as_a_png_beside_the_drive_list` |  | 0.1 s | Screenshot saves the window as a png beside the drive list. |
| `test_main_window.py` | `test_a_screenshot_that_cannot_be_written_says_so` |  |  | A screenshot that cannot be written says so. |
| `test_main_window.py` | `test_screenshot_names_never_overwrite` |  |  | Screenshot names never overwrite. |
| `test_rated.py` | `test_rated_speeds` | 33 |  | Rated speeds. |
| `test_rated.py` | `test_every_entry_is_a_pattern_with_sane_speeds` |  |  | Every entry is a pattern with sane speeds. |
| `test_smart.py` | `test_the_boards_nvme_drive_gives_all_three_values` |  |  | The boards nvme drive gives all three values. |
| `test_smart.py` | `test_the_label_never_holds_the_serial` |  |  | The label never holds the serial. |
| `test_smart.py` | `test_health_is_100_minus_percent_used_and_stops_at_zero` |  |  | Health is 100 minus percent used and stops at zero. |
| `test_smart.py` | `test_a_critical_warning_is_kept` |  |  | A critical warning is kept. |
| `test_smart.py` | `test_sata_drives_and_a_usb_stick_without_smart` |  |  | Sata drives and a usb stick without smart. |
| `test_smart.py` | `test_the_first_known_health_attribute_wins_and_odd_values_are_skipped` |  |  | The first known health attribute wins and odd values are skipped. |
| `test_smart.py` | `test_a_failing_sata_drive_is_flagged` |  |  | A failing sata drive is flagged. |
| `test_smart.py` | `test_a_drive_whose_attributes_fail_keeps_its_properties_and_the_error` |  |  | A drive whose attributes fail keeps its properties and the error. |
| `test_smart.py` | `test_udisks_not_answering_is_an_error_with_its_reason` |  |  | Udisks not answering is an error with its reason. |
| `test_smart.py` | `test_without_busctl` |  |  | Without busctl. |
| `test_smart.py` | `test_sizes_in_decimal_units` | 4 |  | Sizes in decimal units. |
| `test_smart.py` | `test_the_boards_specs` |  |  | The boards specs. |
| `test_smart.py` | `test_the_serial_stays_out_of_the_repr` |  |  | The serial stays out of the repr. |
| `test_smart.py` | `test_sata_and_usb_links_and_the_sata_data_in_sectors` |  |  | Sata and usb links and the sata data in sectors. |
| `test_smart.py` | `test_no_sysfs_leaves_the_speed_empty` |  |  | No sysfs leaves the speed empty. |
| `test_smart.py` | `test_pcie_names` | 4 |  | Pcie names. |
| `test_smart.py` | `test_firmware_updates_from_fwupd` |  |  | Firmware updates from fwupd. |
| `test_smart.py` | `test_without_fwupd_the_update_is_unknown` |  |  | Without fwupd the update is unknown. |
| `test_smart.py` | `test_the_board_holds_the_boards_drive_back` |  |  | The board holds the boards drive back. |
| `test_smart.py` | `test_a_port_fast_enough_and_the_sata_and_usb_ports` |  |  | A port fast enough and the sata and usb ports. |
| `test_smart.py` | `test_the_mount_points_of_each_drive` |  |  | The mount points of each drive. |
| `test_smart.py` | `test_what_a_pcie_link_carries` | 4 |  | What a pcie link carries. |
| `test_smart.py` | `test_an_nvme_enclosure_linked_at_usb_2_in_a_usb_3_port` |  |  | The owner's enclosure: its port does 5 Gb/s (its peer on the USB 3 bus), the drive linked at 480 Mb/s. |
| `test_smart.py` | `test_a_usb_3_drive_in_a_faster_port_has_no_slow_link` |  |  | A usb 3 drive in a faster port has no slow link. |
| `test_speedtest.py` | `test_the_home_folder_when_it_is_on_the_drive` |  |  | The home folder when it is on the drive. |
| `test_speedtest.py` | `test_else_a_writable_mount_point_and_none_unmounted` |  |  | Else a writable mount point and none unmounted. |
| `test_speedtest.py` | `test_it_measures_and_leaves_nothing_behind` |  |  | It measures and leaves nothing behind. |
| `test_speedtest.py` | `test_existing_test_file_is_not_overwritten_or_deleted` |  |  | Existing test file is not overwritten or deleted. |
| `test_speedtest.py` | `test_a_slow_drive_stops_at_the_limit` |  |  | A slow drive stops at the limit. |
| `test_speedtest.py` | `test_not_enough_space_or_no_folder` |  |  | Not enough space or no folder. |

## apps/upscaler

98 tests in 10 files, 1.6 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_acquire.py` | `test_latest_release_parses_github_json` |  |  | Latest release parses github json. |
| `test_acquire.py` | `test_latest_release_takes_helixsrs_own_zip` |  |  | From 1.9.0 on a release also has HelixSR Scaler's zip, whichever comes first. |
| `test_acquire.py` | `test_update_status` |  |  | Update status. |
| `test_acquire.py` | `test_download_verifies_checksum` |  |  | Download verifies checksum. |
| `test_acquire.py` | `test_download_retries_a_busy_server` |  |  | Download retries a busy server. |
| `test_acquire.py` | `test_download_gives_up_after_five_tries` |  |  | Download gives up after five tries. |
| `test_acquire.py` | `test_download_cancel_during_the_pause` |  |  | Download cancel during the pause. |
| `test_acquire.py` | `test_parse_pins_and_extract` |  |  | Parse pins and extract. |
| `test_acquire.py` | `test_extract_zip_rejects_traversal` |  |  | Extract zip rejects traversal. |
| `test_acquire.py` | `test_unpack_prerequisites` |  |  | Unpack prerequisites. |
| `test_acquire.py` | `test_needed_pins` |  |  | Needed pins. |
| `test_acquire.py` | `test_find_dlss_dlls` |  |  | Find dlss dlls. |
| `test_acquire.py` | `test_setup_worker_end_to_end` |  |  | Setup worker end to end. |
| `test_acquire.py` | `test_setup_worker_uses_local_dlss_and_cached_tools` |  |  | Setup worker uses local dlss and cached tools. |
| `test_acquire.py` | `test_setup_worker_reports_script_failure` |  |  | Setup worker reports script failure. |
| `test_acquire.py` | `test_setup_worker_checksum_failure_keeps_nothing` |  |  | Setup worker checksum failure keeps nothing. |
| `test_acquire.py` | `test_setup_worker_release_error` |  |  | Setup worker release error. |
| `test_acquire.py` | `test_update_check_covers_only_helixsr` |  |  | Update check covers only helixsr. |
| `test_acquire.py` | `test_the_newest_release_of_the_supported_major` |  |  | The app sets up 1.x and 2.x (owner, 20-10-2026) and says when a later major is out that it does not. |
| `test_acquire.py` | `test_setup_worker_refuses_another_major` |  |  | Setup worker refuses another major. |
| `test_acquire.py` | `test_setup_worker_needs_free_space` |  |  | Setup worker needs free space. |
| `test_acquire.py` | `test_setup_worker_checks_the_release_zip` |  |  | Setup worker checks the release zip. |
| `test_acquire.py` | `test_setup_worker_gives_the_script_no_input` | 2 |  | Setup worker gives the script no input. |
| `test_acquire.py` | `test_setup_worker_skips_frame_generation_from_1_9` | 4 | 0.1 s | Setup worker skips frame generation from 1 9. |
| `test_acquire.py` | `test_setup_worker_fallback_looks_up_the_pinned_tag` |  |  | Setup worker fallback looks up the pinned tag. |
| `test_acquire.py` | `test_setup_worker_accepts_a_one_file_dll` |  |  | Setup worker accepts a one file dll. |
| `test_acquire.py` | `test_setup_worker_builds_2x_without_its_game_installer` |  |  | HelixSR 2's setup script installs into every game with --yes: the app runs its builder instead, on HelixSR-fsrfg, without frame generation, and takes the DLL from there (owner, 20-10-2026). |
| `test_acquire.py` | `test_setup_worker_2x_failures` | 3 | 0.1 s | Setup worker 2x failures. |
| `test_acquire.py` | `test_the_dxc_wrapper_runs_the_compiler_through_wine` |  |  | Absolute Linux paths become Z:\ paths; Wine runs in its own prefix; a Proton folder may have spaces. |
| `test_acquire.py` | `test_find_wine_takes_proton_first` |  |  | Find wine takes proton first. |
| `test_acquire.py` | `test_the_builders_python` |  |  | As HelixSR's script: the portable Python with numpy, else the system's with numpy, else numpy by pip into the portable one. |
| `test_deploy.py` | `test_find_game_dlls` |  |  | Find game dlls. |
| `test_deploy.py` | `test_deploy_and_remove_round_trip` |  |  | Deploy and remove round trip. |
| `test_deploy.py` | `test_redeploy_keeps_real_original` |  |  | Redeploy keeps real original. |
| `test_deploy.py` | `test_deploy_copies_payload_ini_when_none_given` |  |  | Deploy copies payload ini when none given. |
| `test_deploy.py` | `test_deploy_errors` |  |  | Deploy errors. |
| `test_deploy.py` | `test_remove_refuses_foreign_dll` |  |  | Remove refuses foreign dll. |
| `test_deploy.py` | `test_folder_mode` |  |  | Folder mode. |
| `test_deploy.py` | `test_remove_folder_refuses_replaced_game_dll` |  |  | Remove folder refuses replaced game dll. |
| `test_deploy.py` | `test_deployment_state_detects_problems` |  |  | Deployment state detects problems. |
| `test_deploy.py` | `test_folder_mode_with_a_second_upscaler` |  |  | Folder mode with a second upscaler. |
| `test_deploy.py` | `test_second_upscaler_must_not_be_helixsr` |  |  | Second upscaler must not be helixsr. |
| `test_deploy.py` | `test_deployment_state_after_switching_versions` |  |  | A payload replaced by another release: deployments of an older one are older, of a newer one newer. |
| `test_deploy.py` | `test_one_file_dll` |  |  | HelixSR 1.8+: the network is inside the DLL, so no network files go along, and stale ones are removed. |
| `test_games.py` | `test_dll_version` |  |  | Dll version. |
| `test_games.py` | `test_a_game_that_put_its_own_dll_back` |  |  | A game update or Steam's file check puts the game's DLL back and leaves HelixSR's backup: Original restored, not an older build, and Update older games puts HelixSR back without touching the backup or helixsr.ini. |
| `test_games.py` | `test_update_older_builds` |  |  | Update older builds. |
| `test_games.py` | `test_a_newer_build_is_left_alone` |  |  | Deployments of a newer release than the payload (the fallback picked on the Setup page) are not updated. |
| `test_games.py` | `test_game_scan_states_and_targets` |  |  | Game scan states and targets. |
| `test_games.py` | `test_steam_app_ids` |  |  | Steam app ids. |
| `test_games.py` | `test_game_running` |  |  | Game running. |
| `test_games.py` | `test_scan_can_be_cancelled` |  |  | Scan can be cancelled. |
| `test_games.py` | `test_steam_tools_are_not_games` |  |  | Steam tools are not games. |
| `test_help.py` | `test_the_help_page_shows_the_users_folders_as_home` |  |  | The help page shows the users folders as home. |
| `test_ini.py` | `test_defaults_match_upstream_file` |  |  | Defaults match upstream file. |
| `test_ini.py` | `test_parse_values_and_comments` |  |  | Parse values and comments. |
| `test_ini.py` | `test_render_edits_in_place_and_keeps_comments` |  |  | Render edits in place and keeps comments. |
| `test_ini.py` | `test_render_appends_missing_keys_and_sections` |  |  | Render appends missing keys and sections. |
| `test_ini.py` | `test_round_trip_all_fields` |  |  | Round trip all fields. |
| `test_ini.py` | `test_validate` |  |  | Validate. |
| `test_ini.py` | `test_ini_template_prefers_payload` |  |  | Ini template prefers payload. |
| `test_ini.py` | `test_ignored_fields_per_version` |  |  | Ignored fields per version. |
| `test_ini.py` | `test_new_1_8_keys_are_written_only_when_set` |  |  | New 1 8 keys are written only when set. |
| `test_main_window.py` | `test_pages_render_and_refresh` |  | 0.1 s | Pages render and refresh. |
| `test_main_window.py` | `test_deploy_and_remove_through_deploy_page` |  |  | Deploy and remove through deploy page. |
| `test_main_window.py` | `test_folder_mode_through_deploy_page` |  |  | Folder mode through deploy page. |
| `test_main_window.py` | `test_ini_page_saves_default` |  |  | Ini page saves default. |
| `test_main_window.py` | `test_setup_page_builds_and_imports` |  | 0.1 s | Setup page -> SetupWorker (fake release over file://) -> payload imported, Overview updated. |
| `test_main_window.py` | `test_update_hint_on_overview` |  |  | Update hint on overview. |
| `test_main_window.py` | `test_scan_keeps_steam_selection` |  |  | Scan keeps steam selection. |
| `test_main_window.py` | `test_folder_mode_with_a_second_upscaler` |  |  | Folder mode with a second upscaler. |
| `test_main_window.py` | `test_ini_page_greys_out_what_the_version_ignores` |  |  | Ini page greys out what the version ignores. |
| `test_main_window.py` | `test_setup_page_fallback_choice` |  |  | Setup page fallback choice. |
| `test_main_window.py` | `test_optiscaler_through_deploy_page` |  |  | Optiscaler through deploy page. |
| `test_main_window.py` | `test_optiscaler_sets_and_restores_steam_launch_options` |  |  | Optiscaler sets and restores steam launch options. |
| `test_main_window.py` | `test_launch_options_in_game_mode_are_copied` |  |  | Launch options in game mode are copied. |
| `test_main_window.py` | `test_games_page_runs_a_game_with_helixsr` |  | 0.1 s | Games page runs a game with helixsr. |
| `test_main_window.py` | `test_update_older_games_from_the_overview` |  |  | Update older games from the overview. |
| `test_optiscaler.py` | `test_import_takes_the_optiscaler_folder` |  |  | Import takes the optiscaler folder. |
| `test_optiscaler.py` | `test_find_exe_folder` |  |  | Find exe folder. |
| `test_optiscaler.py` | `test_install_and_remove_put_everything_back` |  |  | Install and remove put everything back. |
| `test_optiscaler.py` | `test_an_existing_optiscaler_keeps_its_name_and_its_ini` |  |  | An existing optiscaler keeps its name and its ini. |
| `test_optiscaler.py` | `test_install_refusals` |  |  | Install refusals. |
| `test_optiscaler.py` | `test_launch_options_are_read_and_set_in_place` |  |  | Launch options are read and set in place. |
| `test_optiscaler.py` | `test_launch_options_refusals` |  |  | Launch options refusals. |
| `test_optiscaler.py` | `test_with_override` | 6 |  | With override. |
| `test_optiscaler.py` | `test_the_record_keeps_the_first_launch_options` |  |  | The record keeps the first launch options. |
| `test_payload.py` | `test_status_of_empty_folder` |  |  | Status of empty folder. |
| `test_payload.py` | `test_import_folder` |  |  | Import folder. |
| `test_payload.py` | `test_import_nested_folder` |  |  | Import nested folder. |
| `test_payload.py` | `test_import_zip` |  |  | Import zip. |
| `test_payload.py` | `test_import_without_network_files_reports_missing` |  |  | Import without network files reports missing. |
| `test_payload.py` | `test_import_refuses_folder_without_dll` |  |  | Import refuses folder without dll. |
| `test_store_steam.py` | `test_store_round_trip` |  |  | Store round trip. |
| `test_store_steam.py` | `test_store_tolerates_garbage` |  |  | Store tolerates garbage. |
| `test_store_steam.py` | `test_steam_libraries_and_games` |  |  | Steam libraries and games. |
| `test_widgets.py` | `test_tooltip_filter_is_removed_when_the_app_quits` |  |  | Tooltip filter is removed when the app quits. |
| `test_widgets.py` | `test_tooltip_border_is_the_outline` |  |  | Framed in the theme's outline, silver, not the accent (owner, 07-11-2026). |

## apps/vita3k

72 tests in 9 files, 4.9 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_emulator.py` | `test_the_pin_points_at_the_build` |  |  | The pin points at the build. |
| `test_emulator.py` | `test_install_and_remove` |  |  | Install and remove. |
| `test_emulator.py` | `test_an_older_build_is_replaced` |  |  | An older build is replaced. |
| `test_emulator.py` | `test_the_appimage_updated_itself` |  |  | Its self-updater writes another build over the AppImage it runs from, in the same folder. |
| `test_emulator.py` | `test_a_different_file_is_refused` |  |  | A different file is refused. |
| `test_emulator.py` | `test_a_failed_install_keeps_the_installed_one` |  |  | A failed install keeps the installed one. |
| `test_emulator.py` | `test_download_errors_say_what_happened` |  |  | Download errors say what happened. |
| `test_emulator.py` | `test_a_newer_vita3k_build` |  |  | A newer vita3k build. |
| `test_games.py` | `test_read_sfo` |  |  | Read sfo. |
| `test_games.py` | `test_a_game_as_vita3k_shows_it` |  |  | A game as vita3k shows it. |
| `test_games.py` | `test_what_is_not_a_game` |  |  | What is not a game. |
| `test_games.py` | `test_the_installed_games` |  |  | The installed games. |
| `test_games.py` | `test_a_failing_card_ends_no_scan` |  |  | A failing card ends no scan. |
| `test_library.py` | `test_fixed_folder_and_the_firmware_files` |  |  | Fixed folder and the firmware files. |
| `test_library.py` | `test_removal_rows` |  |  | Removal rows. |
| `test_main_window.py` | `test_vita3k_is_set_up_once_installed` |  | 0.1 s | Once Vita3K is installed, and while it does not run, the app turns its welcome window and its update check off in config.yml (owner, 03-11-2026); the Log tab says so once, and nothing is written while Vita3K runs. |
| `test_main_window.py` | `test_no_user_name_on_the_screen` |  |  | The user's folders show as ~ (owner, 03-11-2026: the privacy rule): the game folder and Vita3K's storage on the game folder's step, the firmware folder behind its info symbol, and a message with a path in it. |
| `test_main_window.py` | `test_before_installing` |  |  | Before installing. |
| `test_main_window.py` | `test_installed_with_firmware_and_games` |  | 0.1 s | Installed with firmware and games. |
| `test_main_window.py` | `test_no_games_yet` |  | 0.1 s | No games yet. |
| `test_main_window.py` | `test_the_appimage_updated_itself` |  |  | The appimage updated itself. |
| `test_main_window.py` | `test_install_runs_off_the_window` |  | 0.1 s | Install runs off the window. |
| `test_main_window.py` | `test_the_firmware_is_taken_from_the_apps_folder` |  | 0.1 s | The PUP files put in Games/Vita/Firmware are given to Vita3K by themselves, the largest first, one after the other, once Vita3K is installed (owner, 03-11-2026): each file once as it is, not while Vita3K runs. |
| `test_main_window.py` | `test_the_firmware_installed_through_vita3k` |  | 0.3 s | The firmware installed through vita3k. |
| `test_main_window.py` | `test_a_package_installed_through_vita3k` |  | 0.1 s | A package installed through vita3k. |
| `test_main_window.py` | `test_a_vpk_installed_in_vita3ks_window` |  | 0.1 s | A vpk installed in vita3ks window. |
| `test_main_window.py` | `test_vita3ks_window` |  | 0.1 s | Vita3K settings opens Vita3K's own window, through the run wrapper and without a game. |
| `test_main_window.py` | `test_the_steam_link` |  |  | The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the boxes and Start game do, and Steam in it is a link the app opens itself. |
| `test_main_window.py` | `test_steam_added_and_taken_out` |  | 0.3 s | Steam added and taken out. |
| `test_main_window.py` | `test_a_shortcut_of_a_game_no_longer_installed_is_taken_out` |  |  | A shortcut of a game no longer installed is taken out. |
| `test_main_window.py` | `test_no_steam_game_mode_or_no_wrapper` |  | 0.1 s | No steam game mode or no wrapper. |
| `test_main_window.py` | `test_the_blue_look` |  |  | RPCS3 Manager's design (owner, 07-11-2026): the Refresh pill and the boxes in the header, the action pills under the introduction, the tabs; Games Install opens the menu of what to install from. |
| `test_main_window.py` | `test_a_newer_vita3k_is_mentioned` |  | 0.1 s | A newer vita3k is mentioned. |
| `test_main_window.py` | `test_the_log_tab` |  |  | What the window says goes to the Log tab with the time, after what the log file held already. |
| `test_main_window.py` | `test_clear_logs_empties_the_log` |  |  | Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones beside it removed and the Log tab emptied with them, the open page kept. |
| `test_main_window.py` | `test_the_blueprint_layout` |  |  | The managers' design (owner, 18-11-2026, PPSSPP Manager's): the window 900 wide when it opens, which is also its narrowest, and what is in it asks for no more; Play time the last pill of the second row; the six tabs share the whole width, the last one up to the margin, with no line over them; under the header's pills the two links alone, in the type of a pill's caption, each still a link. |
| `test_main_window.py` | `test_the_play_time_in_the_second_row` |  |  | Play time, the last pill of the second row (owner, 18-11-2026): all games together, as Vita3K counts it in its time.xml, each game's time in the tip under its title. |
| `test_main_window.py` | `test_covers_with_the_suites_key` |  | 0.6 s | Steam artwork… keeps the suite's key; Update Steam then looks up the games and puts the cover on the portrait, and a game in Steam not looked up yet makes the button do something again. |
| `test_main_window.py` | `test_remove_game_asks_what_to_keep` |  | 0.2 s | Remove game… (owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked deletes the rows still ticked off the window's thread and says what went and what stayed. |
| `test_main_window.py` | `test_the_settings_tab` |  |  | The Settings tab holds Vita3K's settings in the app (core's settings_page): the values as config.yml holds them, a change written into it at once, and nothing while Vita3K runs. |
| `test_main_window.py` | `test_start_game_starts_the_chosen_game_through_steam` |  | 0.3 s | The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your games through Steam, by its shortcut's number, and the open tab stays open. |
| `test_main_window.py` | `test_the_controller_state_beside_the_title` |  |  | Controller connected or No controller (owner, 18-11-2026: as the other managers show it), from the kernel's list of input devices, looked at again every few seconds; Steam's own virtual controller does not count. |
| `test_run_wrapper.py` | `test_started_by_steam_with_a_real_controller` |  |  | Started by steam with a real controller. |
| `test_run_wrapper.py` | `test_started_by_steam_with_only_steams_controller` |  |  | Started by steam with only steams controller. |
| `test_run_wrapper.py` | `test_started_outside_steam` |  |  | Started outside steam. |
| `test_run_wrapper.py` | `test_started_by_steam_on_a_wayland_desktop` |  |  | Started by steam on a wayland desktop. |
| `test_run_wrapper.py` | `test_without_fusermount_it_unpacks_itself` |  |  | Without fusermount it unpacks itself. |
| `test_run_wrapper.py` | `test_help_and_not_installed` |  |  | Help and not installed. |
| `test_saves.py` | `test_the_saves_are_read_from_their_folders` |  |  | The saves are read from their folders. |
| `test_saves.py` | `test_export_and_import_again` |  |  | Export and import again. |
| `test_saves.py` | `test_what_is_no_save_is_refused` |  |  | What is no save is refused. |
| `test_saves.py` | `test_the_tab_lists_exports_imports_and_deletes` |  |  | The tab lists exports imports and deletes. |
| `test_saves.py` | `test_nothing_is_changed_while_vita3k_runs` |  |  | Nothing is changed while vita3k runs. |
| `test_saves.py` | `test_the_play_time_vita3k_counts` |  |  | The play time vita3k counts. |
| `test_shortcuts.py` | `test_the_launch_line_and_whose_shortcut_it_is` |  |  | The launch line and whose shortcut it is. |
| `test_shortcuts.py` | `test_names_are_unique` |  |  | Names are unique. |
| `test_shortcuts.py` | `test_add_then_take_out` |  | 0.4 s | Add then take out. |
| `test_shortcuts.py` | `test_a_shortcut_taken_out_under_the_name_it_has` |  |  | A shortcut taken out under the name it has. |
| `test_shortcuts.py` | `test_artwork_sizes_with_and_without_the_games_pictures` |  | 0.7 s | Artwork sizes with and without the games pictures. |
| `test_shortcuts.py` | `test_pictures_from_steamgriddb_in_place_of_the_drawn_ones` |  | 0.6 s | Pictures from steamgriddb in place of the drawn ones. |
| `test_userdata.py` | `test_vita3ks_folders_follow_xdg` |  |  | Vita3ks folders follow xdg. |
| `test_userdata.py` | `test_the_config_yml_of_build_4186` |  |  | The config yml of build 4186. |
| `test_userdata.py` | `test_the_storage_where_vita3k_keeps_it` |  |  | The storage where vita3k keeps it. |
| `test_userdata.py` | `test_the_firmware_parts` |  |  | The firmware parts. |
| `test_userdata.py` | `test_what_one_install_wrote` |  |  | What one install wrote. |
| `test_userdata.py` | `test_the_lines_the_app_owns_are_set_in_place` |  |  | The welcome window and the update check off (owner, 03-11-2026): the lines set where build 4186 wrote them, every other line kept; a second run changes nothing; a missing key goes before the end, a missing file is made. |
| `test_userdata.py` | `test_vita3k_running_sees_the_appimages_process` |  |  | Vita3k running sees the appimages process. |
| `test_vita3k_settings.py` | `test_the_defaults_without_a_file` |  |  | The defaults without a file. |
| `test_vita3k_settings.py` | `test_every_default_is_what_build_4186_writes` |  |  | config-4186.yml is the file Vita3K wrote on its first start: each setting's default is the value there. |
| `test_vita3k_settings.py` | `test_a_line_written_and_the_rest_kept` |  |  | A line written and the rest kept. |
| `test_vita3k_settings.py` | `test_every_setting_is_one_of_vita3ks` |  |  | A CHOICE's default is one of its choices; the keys are unique; the boxes in order. |
| `test_vita3k_settings.py` | `test_the_forms_of_a_value` |  |  | The forms of a value. |

## apps/webcam

113 tests in 12 files, 2.5 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_access.py` | `test_rule_names_the_boot_loader_only` |  |  | Rule names the boot loader only. |
| `test_access.py` | `test_install_and_uninstall` |  |  | Install and uninstall. |
| `test_access.py` | `test_an_older_rule_is_offered_again` |  |  | An older rule is offered again. |
| `test_access.py` | `test_main_in_another_root` |  |  | Main in another root. |
| `test_access.py` | `test_a_missing_command_does_not_stop_the_change` |  |  | A missing command does not stop the change. |
| `test_access.py` | `test_command_runs_this_file_through_pkexec` |  |  | Command runs this file through pkexec. |
| `test_access.py` | `test_answer` |  |  | Answer. |
| `test_camera.py` | `test_nothing_plugged_in` |  |  | Nothing plugged in. |
| `test_camera.py` | `test_boot_mode` |  |  | Boot mode. |
| `test_camera.py` | `test_ready_with_its_capture_node_only` |  |  | Ready with its capture node only. |
| `test_camera.py` | `test_another_device_video_node_is_not_the_cameras` |  |  | Another device video node is not the cameras. |
| `test_camera.py` | `test_playstation_camera_on_sonys_adapter` |  |  | Playstation camera on sonys adapter. |
| `test_camera.py` | `test_usb_2_is_too_slow_for_the_video` |  |  | Usb 2 is too slow for the video. |
| `test_camera.py` | `test_other_omnivision_devices_are_not_cameras` |  |  | Other omnivision devices are not cameras. |
| `test_controls.py` | `test_ioctl_numbers` |  |  | Ioctl numbers. |
| `test_controls.py` | `test_list_controls` |  |  | List controls. |
| `test_controls.py` | `test_apply_sets_every_chosen_value_modes_first` |  |  | Apply sets every chosen value modes first. |
| `test_controls.py` | `test_apply_names_what_the_camera_refused` |  |  | Apply names what the camera refused. |
| `test_firmware.py` | `test_each_pin_is_a_commit_and_a_known_file_of_its_model` |  |  | Each pin is a commit and a known file of its model. |
| `test_firmware.py` | `test_known_files_are_keyed_by_sha256` |  |  | Known files are keyed by sha256. |
| `test_firmware.py` | `test_folder_follows_xdg` |  |  | Folder follows xdg. |
| `test_firmware.py` | `test_store_and_read` |  |  | Store and read. |
| `test_firmware.py` | `test_check_refuses_what_cannot_be_firmware` |  |  | Check refuses what cannot be firmware. |
| `test_firmware.py` | `test_download` |  |  | Download. |
| `test_firmware.py` | `test_download_refuses_another_file` |  |  | Download refuses another file. |
| `test_firmware.py` | `test_download_failure` |  |  | Download failure. |
| `test_firmware.py` | `test_the_ps4_cameras_download_goes_in_its_own_file` |  |  | The ps4 cameras download goes in its own file. |
| `test_loader.py` | `test_chunks_cross_64_kib` |  |  | Chunks cross 64 kib. |
| `test_loader.py` | `test_upload` |  |  | Upload. |
| `test_loader.py` | `test_the_start_request_may_go_unanswered` | 4 |  | The start request may go unanswered. |
| `test_loader.py` | `test_other_errors_on_start_are_errors` |  |  | Other errors on start are errors. |
| `test_loader.py` | `test_a_short_transfer_stops_the_upload` |  |  | A short transfer stops the upload. |
| `test_loader.py` | `test_an_empty_file_is_not_sent` |  |  | An empty file is not sent. |
| `test_loader.py` | `test_load_waits_for_the_camera` |  |  | Load waits for the camera. |
| `test_loader.py` | `test_load_finds_the_camera_on_the_other_bus` |  |  | The same socket is 6-1 on the USB 2 bus and 7-1 on the USB 3 bus. |
| `test_loader.py` | `test_load_says_when_the_camera_does_not_come_back` |  |  | Load says when the camera does not come back. |
| `test_loader.py` | `test_load_explains_errors` | 3 |  | Load explains errors. |
| `test_loader.py` | `test_one_upload_at_a_time` |  |  | One upload at a time. |
| `test_loader.py` | `test_reduced_bandwidth_patches_the_video_endpoint_only` |  |  | Reduced bandwidth patches the video endpoint only. |
| `test_loader.py` | `test_a_file_without_one_such_endpoint_is_sent_as_it_is` |  |  | A file without one such endpoint is sent as it is. |
| `test_loader.py` | `test_bursts` |  |  | Bursts. |
| `test_main.py` | `test_nothing_to_do` |  |  | Nothing to do. |
| `test_main.py` | `test_loads_a_waiting_camera` |  |  | Loads a waiting camera. |
| `test_main.py` | `test_without_firmware` |  |  | Without firmware. |
| `test_main.py` | `test_a_failed_load` |  |  | A failed load. |
| `test_main.py` | `test_auto_follows_the_setting` |  |  | Auto follows the setting. |
| `test_main.py` | `test_the_firmware_goes_with_the_chosen_bandwidth` |  |  | The firmware goes with the chosen bandwidth. |
| `test_main.py` | `test_auto_needs_load` |  |  | Auto needs load. |
| `test_main.py` | `test_the_chosen_picture_settings_are_set_after_the_load` |  |  | The chosen picture settings are set after the load. |
| `test_main.py` | `test_settings_survive_a_bad_value` |  |  | Settings survive a bad value. |
| `test_main_window.py` | `test_no_camera` |  | 0.1 s | No camera. |
| `test_main_window.py` | `test_allow_access_is_offered_until_the_rule_is_there` |  |  | Allow access is offered until the rule is there. |
| `test_main_window.py` | `test_an_outdated_rule_is_offered_again` |  |  | An outdated rule is offered again. |
| `test_main_window.py` | `test_allow_access_cancelled` |  |  | Allow access cancelled. |
| `test_main_window.py` | `test_boot_mode_needs_its_firmware` |  |  | Boot mode needs its firmware. |
| `test_main_window.py` | `test_a_camera_that_is_there_gets_no_restart_hint` |  |  | A camera that is there gets no restart hint. |
| `test_main_window.py` | `test_boot_mode_without_access` |  |  | Boot mode without access. |
| `test_main_window.py` | `test_a_slow_port_is_flagged` |  |  | A slow port is flagged. |
| `test_main_window.py` | `test_load_firmware_by_hand` |  |  | Load firmware by hand. |
| `test_main_window.py` | `test_bandwidth_setting` |  |  | Bandwidth setting. |
| `test_main_window.py` | `test_a_failed_load_by_hand_is_shown` |  |  | A failed load by hand is shown. |
| `test_main_window.py` | `test_loads_by_itself_once_per_plug_in` |  |  | Loads by itself once per plug in. |
| `test_main_window.py` | `test_not_by_itself_when_switched_off` |  |  | Not by itself when switched off. |
| `test_main_window.py` | `test_download` |  |  | Download. |
| `test_main_window.py` | `test_download_failure_is_shown` |  |  | Download failure is shown. |
| `test_main_window.py` | `test_use_a_file` |  |  | Use a file. |
| `test_main_window.py` | `test_playstation_camera_gets_its_own_file` |  |  | Playstation camera gets its own file. |
| `test_main_window.py` | `test_ready_camera_and_its_preview` |  |  | Ready camera and its preview. |
| `test_main_window.py` | `test_views_of_a_stereo_frame` |  |  | Views of a stereo frame. |
| `test_main_window.py` | `test_unplugging_stops_the_preview` |  |  | Unplugging stops the preview. |
| `test_main_window.py` | `test_a_preview_failure_is_shown` |  |  | A preview failure is shown. |
| `test_main_window.py` | `test_picture_settings` |  |  | Picture settings. |
| `test_main_window.py` | `test_auto_exposure_is_the_default_and_the_exposure_time_stays_grey` |  |  | Auto exposure is the default and the exposure time stays grey. |
| `test_main_window.py` | `test_chosen_settings_come_back_at_the_next_plug_in` |  |  | Chosen settings come back at the next plug in. |
| `test_main_window.py` | `test_a_refused_setting_is_shown` |  |  | A refused setting is shown. |
| `test_main_window.py` | `test_unreadable_settings` |  |  | Unreadable settings. |
| `test_main_window.py` | `test_the_firmware_check_shows_green_for_a_known_file_orange_for_an_own_one` |  |  | The firmware check shows green for a known file orange for an own one. |
| `test_main_window.py` | `test_show_names_the_lens_of_each_half` |  |  | Show names the lens of each half. |
| `test_main_window.py` | `test_full_screen_shows_the_picture_and_starts_the_preview` |  |  | Full screen shows the picture and starts the preview. |
| `test_main_window.py` | `test_full_screen_zoom_pan_and_gray` |  | 0.1 s | Full screen zoom pan and gray. |
| `test_main_window.py` | `test_full_screen_screenshot_and_recording` |  | 0.1 s | Full screen screenshot and recording. |
| `test_main_window.py` | `test_full_screen_mode_steps_and_a_failure_stays` |  |  | Full screen mode steps and a failure stays. |
| `test_main_window.py` | `test_closing_the_window_ends_a_recording` |  |  | Closing the window ends a recording. |
| `test_modes.py` | `test_one_camera_or_both` |  |  | One camera or both. |
| `test_modes.py` | `test_order_and_default` |  |  | Order and default. |
| `test_modes.py` | `test_chosen_falls_back_to_the_default` |  |  | Chosen falls back to the default. |
| `test_modes.py` | `test_crop` |  |  | Crop. |
| `test_preview.py` | `test_to_image_converts_yuyv` |  |  | To image converts yuyv. |
| `test_preview.py` | `test_complete_frames_are_shown` |  |  | Complete frames are shown. |
| `test_preview.py` | `test_only_damaged_frames_stop_with_the_bandwidth_message` |  |  | Only damaged frames stop with the bandwidth message. |
| `test_preview.py` | `test_no_frames_at_all` |  | 0.1 s | No frames at all. |
| `test_preview.py` | `test_a_busy_camera` |  |  | A busy camera. |
| `test_preview.py` | `test_modes_are_the_yuyv_ones` |  |  | Modes are the yuyv ones. |
| `test_preview.py` | `test_no_mode` |  |  | No mode. |
| `test_preview.py` | `test_the_zoom_steps_and_stops_at_its_ends` |  |  | The zoom steps and stops at its ends. |
| `test_preview.py` | `test_the_zoomed_part_moves_within_the_picture` |  |  | The zoomed part moves within the picture. |
| `test_preview.py` | `test_shown_cuts_and_grays` |  |  | Shown cuts and grays. |
| `test_preview.py` | `test_a_drag_is_a_part_of_the_picture_drawn` |  |  | A drag is a part of the picture drawn. |
| `test_record.py` | `test_a_new_file_is_named_after_the_app_and_the_time` |  |  | A new file is named after the app and the time. |
| `test_record.py` | `test_the_folders_are_the_users_pictures_and_videos` |  |  | The folders are the users pictures and videos. |
| `test_record.py` | `test_a_screenshot_is_a_png_in_a_new_folder` |  |  | A screenshot is a png in a new folder. |
| `test_record.py` | `test_a_screenshot_that_cannot_be_written_says_so` |  |  | A screenshot that cannot be written says so. |
| `test_record.py` | `test_a_recording_is_written_and_reads_back` |  | 1.2 s | A recording is written and reads back. |
| `test_usbfs.py` | `test_ioctl_numbers` |  |  | Ioctl numbers. |
| `test_usbfs.py` | `test_calls` |  |  | Calls. |
| `test_usbfs.py` | `test_errors_carry_the_kernels_errno` |  |  | Errors carry the kernels errno. |
| `test_usbfs.py` | `test_a_missing_node` |  |  | A missing node. |
| `test_v4l2.py` | `test_structure_sizes_and_ioctl_numbers` |  |  | Structure sizes and ioctl numbers. |
| `test_v4l2.py` | `test_every_size_at_each_rate` |  |  | Every size at each rate. |
| `test_v4l2.py` | `test_start_sets_the_size_and_the_exact_rate` |  |  | Start sets the size and the exact rate. |
| `test_v4l2.py` | `test_frames_complete_and_damaged` |  |  | Frames complete and damaged. |
| `test_v4l2.py` | `test_no_frame_within_the_timeout` |  |  | No frame within the timeout. |
| `test_v4l2.py` | `test_a_busy_camera` |  |  | A busy camera. |

## apps/xenia

67 tests in 8 files, 4.2 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_emulator.py` | `test_the_pin_points_at_the_release` |  |  | The pin points at the release. |
| `test_emulator.py` | `test_install_and_remove` |  |  | Install and remove. |
| `test_emulator.py` | `test_an_older_version_is_replaced` |  |  | An older version is replaced. |
| `test_emulator.py` | `test_a_different_file_is_refused` |  |  | A different file is refused. |
| `test_emulator.py` | `test_a_failed_install_keeps_the_installed_one` |  |  | A failed install keeps the installed one. |
| `test_emulator.py` | `test_download_errors_say_what_happened` |  |  | Download errors say what happened. |
| `test_emulator.py` | `test_a_newer_xenia` |  |  | A newer xenia. |
| `test_emulator.py` | `test_xenia_running_sees_the_appimages_process` |  |  | Xenia running sees the appimages process. |
| `test_games.py` | `test_a_disc_image_at_each_place` | 5 |  | A disc image at each place. |
| `test_games.py` | `test_what_is_no_xbox_360_disc_is_not_a_game` |  |  | What is no xbox 360 disc is not a game. |
| `test_games.py` | `test_the_title_id_of_an_xex` |  |  | The title id of an xex. |
| `test_games.py` | `test_an_unpacked_disc_is_its_default_xex` |  |  | An unpacked disc is its default xex. |
| `test_games.py` | `test_a_zar_is_listed_under_its_name` |  |  | A zar is listed under its name. |
| `test_games.py` | `test_games_on_demand_and_arcade_packages` |  |  | Games on demand and arcade packages. |
| `test_games.py` | `test_other_packages_are_no_games` |  |  | Other packages are no games. |
| `test_games.py` | `test_a_package_without_a_name_is_named_after_its_file` |  |  | A package without a name is named after its file. |
| `test_games.py` | `test_the_scan_sorts_finds_once_and_stops_at_a_depth` |  |  | The scan sorts finds once and stops at a depth. |
| `test_games.py` | `test_a_linked_game_is_counted_once` |  |  | A linked game is counted once. |
| `test_games.py` | `test_a_failing_card_ends_no_scan` |  |  | A failing card ends no scan. |
| `test_library.py` | `test_fixed_folders` |  |  | Fixed folders. |
| `test_library.py` | `test_removal_rows` |  |  | Removal rows. |
| `test_main_window.py` | `test_before_installing` |  | 0.1 s | Before installing. |
| `test_main_window.py` | `test_installed_with_games` |  |  | Installed with games. |
| `test_main_window.py` | `test_an_older_build_is_offered_the_pinned_one` |  |  | An older build is offered the pinned one. |
| `test_main_window.py` | `test_the_apps_own_game_folders` |  |  | The games are put in Games/XBOX360 in the home folder, made when the app opens, and in Games/XBOX360 on a removable drive that has one (owner, 03-11-2026: fixed folders, no folder choosing); no folder is chosen or remembered any more. |
| `test_main_window.py` | `test_install_runs_off_the_window` |  | 0.1 s | Install runs off the window. |
| `test_main_window.py` | `test_a_failed_install_says_so` |  |  | A failed install says so. |
| `test_main_window.py` | `test_remove` |  |  | Remove. |
| `test_main_window.py` | `test_xenias_window` |  |  | Xenia settings opens Xenia's own window, through the run wrapper and without a game. |
| `test_main_window.py` | `test_the_steam_link` |  |  | The info symbol under the games (owner, 18-11-2026, in place of the line of text): a click shows what the boxes and Start game do, and Steam in it is a link the app opens itself. |
| `test_main_window.py` | `test_steam_added_and_taken_out` |  | 0.3 s | Steam added and taken out. |
| `test_main_window.py` | `test_a_shortcut_of_a_game_no_longer_found_is_taken_out` |  |  | A shortcut of a game no longer found is taken out. |
| `test_main_window.py` | `test_games_need_xenia_for_game_mode` |  |  | Games need xenia for game mode. |
| `test_main_window.py` | `test_no_steam_game_mode_or_no_wrapper` |  | 0.1 s | No steam game mode or no wrapper. |
| `test_main_window.py` | `test_the_blue_look` |  | 0.1 s | RPCS3 Manager's design (owner, 07-11-2026): the Refresh pill and the boxes in the header, the action pills under the introduction, a third of the width each, the tabs. |
| `test_main_window.py` | `test_a_newer_build_is_mentioned` |  |  | A newer build is mentioned. |
| `test_main_window.py` | `test_the_log_tab` |  |  | What the window says goes to the Log tab with the time, after what the log file held already. |
| `test_main_window.py` | `test_clear_logs_empties_the_log` |  |  | Clear logs, the tab beside Log that is a button (owner, 18-11-2026): the log file emptied, the older ones beside it removed and the Log tab emptied with them, the open page kept. |
| `test_main_window.py` | `test_the_blueprint_layout` |  |  | The managers' design (owner, 18-11-2026, PPSSPP Manager's): the window 900 wide when it opens, which is also its narrowest, and what is in it asks for no more (no Play time: Xenia counts none); the six tabs share the whole width, the last one up to the margin, with no line over them; under the header's pills the two links alone, in the type of a pill's caption, each still a link. |
| `test_main_window.py` | `test_covers_with_the_suites_key` |  | 0.9 s | Steam artwork… keeps the suite's key; Update Steam then looks up the game by its title and puts SteamGridDB's pictures in place of all four drawn ones, and a game in Steam not looked up yet makes the button do something again. |
| `test_main_window.py` | `test_remove_game_asks_what_to_keep` |  | 0.1 s | Remove game… (owner, 03-11-2026): the keep window lists what would go; Cancel deletes nothing, Delete marked deletes the rows still ticked off the window's thread and says what went and what stayed. |
| `test_main_window.py` | `test_the_settings_tab` |  |  | The Settings tab holds Xenia's settings in the app (core's settings_page): Xenia's defaults while there is no file, a change written into Xenia's own folder at once, and nothing while Xenia runs. |
| `test_main_window.py` | `test_start_game_starts_the_chosen_game_through_steam` |  | 0.3 s | The Start game tab (owner, 12-11-2026), a tab that is a button: a click starts the game chosen under Your games through Steam, by its shortcut's number, and the open tab stays open. |
| `test_main_window.py` | `test_the_controller_state_beside_the_title` |  |  | Controller connected or No controller (owner, 18-11-2026: as the other managers show it), from the kernel's list of input devices, looked at again every few seconds; Steam's own virtual controller does not count. |
| `test_run_wrapper.py` | `test_started_by_steam_with_a_real_controller` |  |  | Started by steam with a real controller. |
| `test_run_wrapper.py` | `test_started_by_steam_with_only_steams_controller` |  |  | Started by steam with only steams controller. |
| `test_run_wrapper.py` | `test_started_outside_steam` |  |  | Started outside steam. |
| `test_run_wrapper.py` | `test_without_fusermount_it_unpacks_itself` |  |  | Without fusermount it unpacks itself. |
| `test_run_wrapper.py` | `test_not_installed` |  |  | Not installed. |
| `test_run_wrapper.py` | `test_a_game_that_is_gone_is_not_started` |  |  | A shortcut to a game renamed, moved or deleted (owner, 03-11-2026): the emulator is not started, the wrapper says so and ends with 1, so Steam sees the game end; without the app's Python, the words go to stderr alone. |
| `test_saves.py` | `test_the_saves_are_read_from_their_folders` |  |  | The saves are read from their folders. |
| `test_saves.py` | `test_export_and_import_again_with_the_headers` |  |  | Export and import again with the headers. |
| `test_saves.py` | `test_what_is_no_save_or_has_no_profile_is_refused` |  |  | What is no save or has no profile is refused. |
| `test_saves.py` | `test_delete_takes_the_header_too` |  |  | Delete takes the header too. |
| `test_saves.py` | `test_the_tab_lists_exports_imports_and_deletes` |  |  | The tab lists exports imports and deletes. |
| `test_saves.py` | `test_no_profile_yet_and_nothing_changed_while_xenia_runs` |  |  | No profile yet and nothing changed while xenia runs. |
| `test_shortcuts.py` | `test_the_launch_line_and_whose_shortcut_it_is` |  |  | The launch line and whose shortcut it is. |
| `test_shortcuts.py` | `test_names_are_unique` |  |  | Names are unique. |
| `test_shortcuts.py` | `test_add_then_take_out` |  | 0.5 s | Add then take out. |
| `test_shortcuts.py` | `test_a_shortcut_taken_out_under_the_name_it_has` |  |  | A shortcut taken out under the name it has. |
| `test_shortcuts.py` | `test_the_drawn_artwork` |  | 0.3 s | The drawn artwork. |
| `test_shortcuts.py` | `test_pictures_from_steamgriddb_in_place_of_the_drawn_ones` |  | 0.8 s | Pictures from steamgriddb in place of the drawn ones. |
| `test_xenia_settings.py` | `test_the_defaults_without_a_file` |  |  | The defaults without a file. |
| `test_xenia_settings.py` | `test_a_value_written_in_xenias_layout` |  |  | A value written in xenias layout. |
| `test_xenia_settings.py` | `test_a_key_or_a_section_the_file_lacks` |  |  | A key or a section the file lacks. |
| `test_xenia_settings.py` | `test_every_setting_is_one_of_xenias` |  |  | The sections and defaults as build e6cd2e4 defines them; a CHOICE's default is one of its choices; the choices the Linux build has. |
| `test_xenia_settings.py` | `test_the_forms_of_a_value` |  |  | The forms of a value. |

## core

174 tests in 25 files, 3.5 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_action_tab.py` | `test_it_is_the_last_tab_with_its_name_and_tooltip` |  |  | It is the last tab with its name and tooltip. |
| `test_action_tab.py` | `test_a_click_acts_and_the_open_page_stays` |  |  | A click acts and the open page stays. |
| `test_action_tab.py` | `test_the_keyboard_passes_it_by` |  |  | The keyboard passes it by. |
| `test_action_tab.py` | `test_a_press_beside_the_tabs_does_nothing` |  |  | A press beside the tabs does nothing. |
| `test_action_tab.py` | `test_two_action_tabs_in_one_row` |  |  | Clear logs beside Start game (owner, 18-11-2026): each acts on its own click, and neither sends the tabs to the other. |
| `test_app_help.py` | `test_create_app_sets_names_and_current` |  |  | Create app sets names and current. |
| `test_app_help.py` | `test_org_only_when_declared` |  |  | Org only when declared. |
| `test_app_help.py` | `test_help_view` |  |  | Help view. |
| `test_app_settings.py` | `test_an_ini_app_leaves_the_default_format_alone` |  |  | An ini app leaves the default format alone. |
| `test_appinfo.py` | `test_defaults` |  |  | Defaults. |
| `test_appinfo.py` | `test_existing_settings_names_are_kept` |  |  | Existing settings names are kept. |
| `test_applog.py` | `test_the_file_and_its_lines` |  |  | The file and its lines. |
| `test_applog.py` | `test_an_uncaught_error_is_logged` |  |  | An uncaught error is logged. |
| `test_applog.py` | `test_without_a_folder_the_log_goes_to_stderr` |  |  | Without a folder the log goes to stderr. |
| `test_applog.py` | `test_a_private_log_masks_the_users_folders` |  |  | private=True (owner, 29-10-2026): no user name in a line. |
| `test_applog.py` | `test_clear_empties_the_log_and_the_older_ones` |  |  | Clear logs (owner, 18-11-2026): the file emptied while it stays the app's log, the older ones removed. |
| `test_covers.py` | `test_the_key_for_the_whole_suite` |  |  | The key for the whole suite. |
| `test_covers.py` | `test_the_key_dialog` |  |  | The key dialog. |
| `test_covers.py` | `test_names_and_titles` |  |  | Names and titles. |
| `test_covers.py` | `test_the_exact_name_else_the_first_found` |  |  | The exact name else the first found. |
| `test_covers.py` | `test_the_picture_with_the_highest_score_of_the_kinds_kept` |  |  | The picture with the highest score of the kinds kept. |
| `test_covers.py` | `test_pictures_are_kept_and_not_asked_for_again` |  |  | Pictures are kept and not asked for again. |
| `test_covers.py` | `test_only_the_kinds_asked_for` |  |  | Only the kinds asked for. |
| `test_covers.py` | `test_a_game_with_no_pictures_is_not_asked_for_again` |  |  | A game with no pictures is not asked for again. |
| `test_covers.py` | `test_no_lookup_after_a_refused_key_or_no_network` | 3 |  | No lookup after a refused key or no network. |
| `test_covers.py` | `test_a_picture_that_does_not_download_is_asked_for_again` |  |  | A picture that does not download is asked for again. |
| `test_covers.py` | `test_the_pictures_fitted_to_steams_sizes` |  | 0.3 s | The pictures fitted to steams sizes. |
| `test_drives.py` | `test_removable_drives_are_the_mount_points_under_the_media_folders` |  |  | udisks mounts a drive at /run/media/<user>/<drive>, Bazzite's media-automount at /run/media/system/<drive> (media-automount links to it): each mount point once, a plain folder never, a missing root skipped. |
| `test_drives.py` | `test_game_folders_are_made_and_found` |  |  | Game folders are made and found. |
| `test_exit_keys.py` | `test_escape_closes_the_window_from_the_widget_with_the_focus` |  |  | Escape closes the window from the widget with the focus. |
| `test_exit_keys.py` | `test_another_key_and_escape_with_a_modifier_do_nothing` |  |  | Another key and escape with a modifier do nothing. |
| `test_exit_keys.py` | `test_the_windows_own_escape_comes_first` |  |  | The windows own escape comes first. |
| `test_exit_keys.py` | `test_a_window_that_refuses_to_close_stays` |  |  | A window that refuses to close stays. |
| `test_exit_keys.py` | `test_a_dialog_a_menu_and_a_window_that_keeps_its_keys_are_left_alone` |  |  | A dialog a menu and a window that keeps its keys are left alone. |
| `test_exit_keys.py` | `test_a_dialog_keeps_qts_escape` |  |  | A dialog keeps qts escape. |
| `test_exit_keys.py` | `test_b_is_escape_for_the_app_with_the_focus` |  |  | B is escape for the app with the focus. |
| `test_exit_keys.py` | `test_b_without_the_focus_is_read_and_dropped` |  |  | B without the focus is read and dropped. |
| `test_exit_keys.py` | `test_b_right_after_the_focus_came_is_the_press_that_closed_another_app` |  |  | B right after the focus came is the press that closed another app. |
| `test_exit_keys.py` | `test_b_closes_a_dialog_before_the_window` |  |  | B closes a dialog before the window. |
| `test_exit_keys.py` | `test_without_a_controller_reader_there_is_escape_alone` |  |  | Without a controller reader there is escape alone. |
| `test_exit_keys.py` | `test_a_reader_that_fails_is_stopped_and_the_app_goes_on` |  |  | A reader that fails is stopped and the app goes on. |
| `test_exit_keys.py` | `test_stop_closes_the_reader` |  |  | Stop closes the reader. |
| `test_exit_keys.py` | `test_sdls_variables_do_not_stay_in_the_environment` |  | 0.1 s | What the app starts later (Steam, an emulator) must not inherit SDL's dummy video driver; a value that was there before (from the portal that started the app) stays as it was. |
| `test_exit_keys.py` | `test_install_gives_the_app_its_exit_keys` |  |  | Install gives the app its exit keys. |
| `test_gamepad.py` | `test_the_buttons_the_window_acts_on` |  |  | The buttons the window acts on. |
| `test_gamepad.py` | `test_a_held_direction_repeats` |  |  | A held direction repeats. |
| `test_gamepad.py` | `test_the_left_stick_moves_the_right_stick_does_not` |  |  | The left stick moves the right stick does not. |
| `test_gamepad.py` | `test_every_control_as_it_is` |  |  | For the controller test: buttons pressed and let go, the sticks from -1 to 1, the triggers from 0 to 1. |
| `test_gamepad.py` | `test_rt_pulled_is_one_press` |  |  | RT is the portal's Steam (owner, 30-10-2026): past halfway it is pressed, once, until it is let go (under 0.3). |
| `test_gamepad.py` | `test_lt_pulled_is_one_press_of_its_own` |  |  | LT is the portal's Screen (owner, 31-10-2026), pressed as RT is, each trigger on its own. |
| `test_gamepad.py` | `test_an_unplugged_pad_stops_a_held_direction` |  |  | An unplugged pad stops a held direction. |
| `test_gamepad.py` | `test_stick_direction` |  |  | Stick direction. |
| `test_gamepad.py` | `test_without_pygame_or_a_controller` |  |  | Without pygame or a controller. |
| `test_gone.py` | `test_the_desktop_message_names_the_file_and_what_to_do` |  |  | The desktop message names the file and what to do. |
| `test_instance.py` | `test_server_name_is_per_app_and_user` |  |  | Server name is per app and user. |
| `test_instance.py` | `test_nobody_running` |  |  | Nobody running. |
| `test_instance.py` | `test_forward_reaches_listener` |  |  | Forward reaches listener. |
| `test_instance.py` | `test_second_launch_raises_the_window` |  |  | Second launch raises the window. |
| `test_instance.py` | `test_launch_without_arguments_sends_the_plain_show_request` |  |  | Launch without arguments sends the plain show request. |
| `test_instance.py` | `test_second_launch_hands_over_its_arguments` |  |  | Second launch hands over its arguments. |
| `test_instance.py` | `test_arguments_without_a_handler_or_malformed_only_show` |  | 0.1 s | Arguments without a handler or malformed only show. |
| `test_instance.py` | `test_first_launch_takes_the_lock` |  |  | First launch takes the lock. |
| `test_instance.py` | `test_launch_during_startup_waits_instead_of_opening_a_second_window` |  | 0.3 s | Launch during startup waits instead of opening a second window. |
| `test_keep.py` | `test_every_row_starts_as_delete_and_a_turns_it_to_keep_and_back` |  |  | Every row starts as delete and a turns it to keep and back. |
| `test_keep.py` | `test_rows_say_the_mark_what_it_is_and_the_size` |  |  | Rows say the mark what it is and the size. |
| `test_keep.py` | `test_sizes_read_as_a_person_reads_them` |  |  | Sizes read as a person reads them. |
| `test_keep.py` | `test_a_missing_path_has_no_size` |  |  | A missing path has no size. |
| `test_keep.py` | `test_delete_takes_files_and_folders_read_only_ones_too` |  |  | Delete takes files and folders read only ones too. |
| `test_keep_dialog.py` | `test_the_rows_and_their_marks` |  |  | The rows and their marks. |
| `test_nexus.py` | `test_amsterdam_time_is_cet_in_winter_and_cest_in_summer` |  |  | Amsterdam time is cet in winter and cest in summer. |
| `test_nexus.py` | `test_the_stamp_names_the_commit_and_its_time` |  |  | The stamp names the commit and its time. |
| `test_nexus.py` | `test_the_header_shows_the_stamp_without_a_version` |  |  | The header shows the stamp without a version. |
| `test_platform.py` | `test_terminal_command_plain_keeps_window_open` |  |  | Terminal command plain keeps window open. |
| `test_platform.py` | `test_terminal_command_exit_file_covers_whole_command` |  |  | Terminal command exit file covers whole command. |
| `test_platform.py` | `test_terminal_command_on_error_pauses_only_after_a_failure` |  |  | keep_open="on_error" (owner, 26-10-2026): the window of a command that ended well closes by itself, one with an error waits for Enter; the exit file gets the status either way. |
| `test_platform.py` | `test_on_error_runs_the_pause_only_on_a_failure` | 3 |  | On error runs the pause only on a failure. |
| `test_platform.py` | `test_exit_file_gets_the_status` | 3 |  | Exit file gets the status. |
| `test_platform.py` | `test_no_terminal_raises` |  |  | No terminal raises. |
| `test_platform.py` | `test_terminal_preference_and_argv` |  |  | Terminal preference and argv. |
| `test_platform.py` | `test_expand_and_xdg` |  |  | Expand and xdg. |
| `test_platform.py` | `test_show_in_folder` |  |  | A saved screenshot shows itself (owner, 06-11-2026): the file manager over D-Bus, else the folder with xdg-open. |
| `test_platform.py` | `test_private_writes_the_home_folder_as_a_tilde` |  |  | The privacy rule (owner, 29-10-2026: a folder on the screen showed the user's name): the home folder as ~, wherever it is in the text. |
| `test_renamed.py` | `test_a_game_is_its_code_else_its_size` |  |  | A game is its code else its size. |
| `test_renamed.py` | `test_the_games_in_steam_are_kept_and_the_ones_no_longer_in_steam_forgotten` |  |  | The games in steam are kept and the ones no longer in steam forgotten. |
| `test_renamed.py` | `test_a_game_found_again_takes_the_mark_when_it_is_the_only_match` |  |  | A game found again takes the mark when it is the only match. |
| `test_settings.py` | `test_native_file_matches_old_location` |  |  | Native file matches old location. |
| `test_settings.py` | `test_ini_and_org_override` |  |  | Ini and org override. |
| `test_settings.py` | `test_geometry_round_trip` |  |  | Geometry round trip. |
| `test_settings.py` | `test_store_types_and_change_signal` |  |  | Store types and change signal. |
| `test_settings_page.py` | `test_the_boxes_the_values_and_a_change` |  |  | The boxes the values and a change. |
| `test_settings_page.py` | `test_a_value_the_app_does_not_offer_is_shown_as_it_is` |  |  | A value the app does not offer is shown as it is. |
| `test_settings_page.py` | `test_nothing_is_written_while_the_emulator_runs_or_the_file_refuses` |  |  | Nothing is written while the emulator runs or the file refuses. |
| `test_settings_page.py` | `test_the_window_holds_the_page` |  |  | The window holds the page. |
| `test_sound.py` | `test_the_volume_bazzite_remembers` |  |  | A line per stream, the volume and mute as JSON; a space in an application's name is a backslash and an s. |
| `test_sound.py` | `test_the_state_home` |  |  | The state home. |
| `test_sound.py` | `test_the_words` |  |  | The words. |
| `test_sound.py` | `test_unmute_without_a_stream_playing` |  |  | No stream of the emulator plays: a silent one is opened under its name (WirePlumber gives it the remembered mute), unmuted with pactl, and WirePlumber's stored value read back (the way proved on the board, 24-10-2026: 2 s from muted to stored unmuted). |
| `test_sound.py` | `test_unmute_the_stream_that_plays` |  |  | Unmute the stream that plays. |
| `test_sound.py` | `test_unmute_says_what_went_wrong` |  |  | Unmute says what went wrong. |
| `test_steam.py` | `test_the_binary_format_by_hand` |  |  | The binary format by hand. |
| `test_steam.py` | `test_the_entry_and_its_appid` |  |  | The entry and its appid. |
| `test_steam.py` | `test_the_shortcut_icon_is_the_png_beside_a_webp_icon` |  |  | The shortcut icon is the png beside a webp icon. |
| `test_steam.py` | `test_several_shortcuts_in_one_write` |  |  | Several shortcuts in one write. |
| `test_steam.py` | `test_update_keeps_the_play_time_and_remove_takes_the_artwork` |  |  | Update keeps the play time and remove takes the artwork. |
| `test_steam.py` | `test_a_shortcut_of_another_program_taken_out_takes_its_artwork` |  |  | A shortcut made before a game manager's play mode starts the emulator itself, so its number is another's than the change that takes it out (30-10-2026): the artwork under the number it has goes. |
| `test_steam.py` | `test_a_rename_keeps_artwork_whose_number_is_taken_again` |  |  | Two shortcuts that swap names: each number is in use after the change, so no artwork goes. |
| `test_steam.py` | `test_no_users_and_a_damaged_file` |  |  | No users and a damaged file. |
| `test_steam.py` | `test_find_steam` |  |  | Find steam. |
| `test_steam.py` | `test_closed_for_a_change_and_started_again` |  |  | Closed for a change and started again. |
| `test_steam.py` | `test_steam_that_does_not_close_changes_nothing` |  |  | Steam that does not close changes nothing. |
| `test_steam.py` | `test_steam_running_reads_process_names` |  |  | Steam running reads process names. |
| `test_steam.py` | `test_game_mode` |  |  | Game mode. |
| `test_steam.py` | `test_steam_closes_with_its_own_command` |  |  | Steam closes with its own command. |
| `test_steam.py` | `test_installed_is_steams_program` |  |  | The portal's RT Steam shows only where Steam's program is (owner, 30-10-2026). |
| `test_steam.py` | `test_a_shortcut_is_started_by_its_game_id` |  |  | A game started from its manager goes through Steam (owner, 29-10-2026): steam://rungameid/ with the shortcut's appid in the high half. |
| `test_steam.py` | `test_the_number_of_a_shortcut_as_steams_file_has_it` |  |  | What Start game hands to play_url() (owner, 12-11-2026): the shortcut's appid from Steam's own file, its 32 bits; from its program and name when the file names none; None for a game that has no shortcut. |
| `test_steam_art.py` | `test_steams_sizes_and_the_icon_as_logo` |  | 0.3 s | Steams sizes and the icon as logo. |
| `test_steam_art.py` | `test_a_webp_icon_is_the_logo_as_png` |  | 0.3 s | Steam's grid files are PNG: an app's WebP icon goes in as PNG, the same picture. |
| `test_steam_art.py` | `test_the_background_takes_the_icons_colour` |  | 0.6 s | The background takes the icons colour. |
| `test_steam_art.py` | `test_a_long_title_fits` |  | 0.3 s | A long title fits. |
| `test_steam_art.py` | `test_without_the_icon` |  | 0.3 s | Without the icon. |
| `test_text.py` | `test_fmt_numbered_and_reordered` |  |  | Fmt numbered and reordered. |
| `test_text.py` | `test_fmt_single_pass_and_out_of_range` |  |  | Fmt single pass and out of range. |
| `test_text.py` | `test_fill_only_known_names` |  |  | Fill only known names. |
| `test_text.py` | `test_fill_single_pass` |  |  | Fill single pass. |
| `test_text.py` | `test_plain_tooltip_escapes` |  |  | Plain tooltip escapes. |
| `test_text.py` | `test_window_title` |  |  | Window title. |
| `test_theme.py` | `test_the_default_is_gunmetal` |  |  | The default is gunmetal. |
| `test_theme.py` | `test_a_chosen_theme_is_kept` |  |  | A chosen theme is kept. |
| `test_theme.py` | `test_an_unknown_theme_is_the_default` |  |  | An unknown theme is the default. |
| `test_theme.py` | `test_three_themes` |  |  | Three themes. |
| `test_theme.py` | `test_the_file_follows_xdg_config_home` |  |  | The file follows xdg config home. |
| `test_theme.py` | `test_apply_theme` | 3 |  | Apply theme. |
| `test_theme.py` | `test_surface_style` |  |  | Surface style. |
| `test_theme.py` | `test_muted_lies_between_text_and_window` | 3 |  | Muted lies between text and window. |
| `test_theme.py` | `test_hover_focus_and_chosen_borders_are_silver` |  |  | Every border under the mouse, with the focus or on the chosen tab is silver (owner, 05-11-2026), a darker silver on the light theme, never the accent; a theme without an outline of its own (Nexus's) keeps its accent. |
| `test_updates.py` | `test_repo_slug` |  |  | Repo slug. |
| `test_updates.py` | `test_version_tuple` |  |  | Version tuple. |
| `test_updates.py` | `test_latest_without_prefix_uses_latest_endpoint` |  |  | Latest without prefix uses latest endpoint. |
| `test_updates.py` | `test_prefix_picks_this_apps_newest_release` |  |  | Prefix picks this apps newest release. |
| `test_updates.py` | `test_prefix_without_match` |  |  | Prefix without match. |
| `test_updates.py` | `test_prefix_follows_pages_until_found` |  |  | Prefix follows pages until found. |
| `test_updates.py` | `test_prefix_stops_at_the_last_page` |  |  | Prefix stops at the last page. |
| `test_updates.py` | `test_prefix_gives_up_after_max_pages` |  |  | Prefix gives up after max pages. |
| `test_updates.py` | `test_errors_never_raise` | 2 |  | Errors never raise. |
| `test_updates.py` | `test_unexpected_tag` |  |  | Unexpected tag. |
| `test_updates.py` | `test_status` | 4 |  | Status. |
| `test_updates.py` | `test_checker_runs_job_off_thread` |  |  | Checker runs job off thread. |
| `test_widgets.py` | `test_status_pill_colours` |  |  | The theme's surface; the state a colored left edge, the edge's color for neutral. |
| `test_widgets.py` | `test_status_text_colours` |  |  | Status text colours. |
| `test_widgets.py` | `test_metric_box` |  |  | Metric box. |
| `test_widgets.py` | `test_pill_is_a_metric_box_that_clicks` |  |  | A click, Enter or Space emits clicked; the silver outline under the mouse or the keyboard focus. |
| `test_widgets.py` | `test_a_pill_that_cannot_be_clicked_looks_muted` |  |  | Only a disabled pill's text is muted (a rule on the pill's own state would mute every pill: Qt ignores an ancestor's pseudo-state); enabled again, it is bright again. |
| `test_widgets.py` | `test_same_width_follows_the_widest` |  |  | Same width follows the widest. |
| `test_widgets.py` | `test_set_button_active_keeps_height` |  |  | Set button active keeps height. |
| `test_widgets.py` | `test_accent_button` |  |  | Accent button. |
| `test_widgets.py` | `test_terminal_follows_end_only_when_at_end` |  |  | Terminal follows end only when at end. |
| `test_widgets.py` | `test_text_dialog` |  |  | Text dialog. |
| `test_widgets.py` | `test_tooltip_follows_window_and_survives_its_deletion` |  |  | Tooltip follows window and survives its deletion. |
| `test_widgets.py` | `test_long_tooltip_wraps` |  |  | Long tooltip wraps. |
| `test_widgets.py` | `test_tooltip_border_is_the_outline` |  |  | Framed in the theme's outline, silver in the suite's themes, not the accent (owner, 07-11-2026); a theme without an outline of its own (Nexus's) keeps its accent. |
| `test_widgets.py` | `test_tooltip_never_covers_the_cursor` |  |  | Tooltip never covers the cursor. |
| `test_widgets.py` | `test_tooltip_lets_clicks_through` |  |  | Tooltip lets clicks through. |
| `test_widgets.py` | `test_item_view_tooltip_text` |  |  | Item view tooltip text. |
| `test_widgets.py` | `test_tab_tooltip_text` |  |  | A tab's tooltip (setTabToolTip) in the rounded style too (owner, 26-10-2026: the portal's tabs showed Qt's plain one); between the tabs the bar's own, or nothing. |
| `test_widgets.py` | `test_tooltip_filter_is_removed_when_the_app_quits` |  |  | Tooltip filter is removed when the app quits. |
| `test_widgets.py` | `test_tooltip_filter_is_removed_by_uninstall` |  |  | The test sessions' teardown (conftest.py): the app's filter off, so it sees no more events. |
| `test_widgets.py` | `test_manual_tooltip_uses_installed_instance` |  |  | Manual tooltip uses installed instance. |
| `test_widgets.py` | `test_app_header_layout` |  |  | Icon at 96 px spanning the title row (name, version, states, actions) and the second row. |
| `test_widgets.py` | `test_app_header_title_lines_up_with_the_second_row` |  |  | The title's text starts where the second row's does: no padding pushes it to the right. |
| `test_widgets.py` | `test_a_wrapped_labels_minimum_height_follows_its_width` |  |  | A plain wrapped QLabel reports one line as its minimum, whatever it wraps to; a WrappedLabel reports the lines it needs at its width (owner, 24-10-2026: the Settings tab squeezed under a three-line introduction). |
| `test_widgets.py` | `test_an_apps_own_theme` |  |  | An app that is not a suite's (Nexus Releases) draws the widgets with its own theme: the surfaces, the muted text and the accent follow set_theme(), and create_app(theme=) sets it (owner, 26-10-2026: a Nexus app takes Nexus's design). |
| `test_widgets.py` | `test_info_button_opens_its_text_below_it` |  |  | The info symbol (owner, 01-11-2026): a click opens the text in a popup that stays; links work in it. |
| `test_widgets.py` | `test_action_pill_stands_in_for_a_button` |  |  | Action pill stands in for a button. |

## dev/dash

50 tests in 6 files, 2.3 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_icons.py` | `test_a_suite_with_category_icons_is_told_apart` |  |  | A suite with category icons is told apart. |
| `test_icons.py` | `test_whole_set_runs_first_then_each_size_in_order` |  |  | Whole set runs first then each size in order. |
| `test_icons.py` | `test_icon_names_match_the_nexus_tool` |  |  | Icon names match the nexus tool. |
| `test_icons.py` | `test_dialog_runs_the_conversions_and_shows_their_output` |  |  | Dialog runs the conversions and shows their output. |
| `test_icons.py` | `test_dialog_stops_at_the_first_failure` |  |  | Dialog stops at the first failure. |
| `test_icons.py` | `test_dialog_on_a_suite_without_category_icons_is_greyed_out` |  |  | Dialog on a suite without category icons is greyed out. |
| `test_icons.py` | `test_dialog_converts_real_images_in_a_copy_of_the_icons` |  | 0.3 s | The whole way, with the suite's own tool on a copy of its icons and the apps' copies. |
| `test_issues.py` | `test_open_issues_without_pull_requests` |  |  | GitHub's issues list holds the pull requests too: Close issues shows the issues only. |
| `test_issues.py` | `test_close_commands` |  |  | Close commands. |
| `test_issues.py` | `test_the_dialog_lists_the_open_ones_and_ticks` |  |  | The dialog lists the open ones and ticks. |
| `test_issues.py` | `test_the_tile_opens_the_dialog_and_closes_the_ticked` |  | 0.1 s | The tile opens the dialog and closes the ticked. |
| `test_issues.py` | `test_close_issues_runs_gh_for_each_in_turn` |  | 0.1 s | Close issues runs gh for each in turn. |
| `test_issues.py` | `test_close_issues_without_gh_closes_nothing` |  |  | Close issues without gh closes nothing. |
| `test_issues.py` | `test_a_gh_that_does_not_start_is_said` |  |  | A gh that does not start is said. |
| `test_local.py` | `test_launch_targets` |  |  | Launch targets. |
| `test_local.py` | `test_changes_board_follows_the_manifest` |  |  | Changes board follows the manifest. |
| `test_local.py` | `test_portal_target` |  |  | Portal target. |
| `test_local.py` | `test_this_checkouts_portal` |  |  | This checkouts portal. |
| `test_local.py` | `test_docs_target` |  |  | Docs target. |
| `test_local.py` | `test_docs_target_on_the_network` |  |  | Docs target on the network. |
| `test_local.py` | `test_network_addresses_leave_out_loopback` |  |  | Network addresses leave out loopback. |
| `test_local.py` | `test_the_portal_is_the_first_icon_then_the_apps_then_the_wiki` |  |  | The portal is the first icon then the apps then the wiki. |
| `test_local.py` | `test_a_click_runs_an_app_from_the_checkout` |  |  | A click runs an app from the checkout. |
| `test_local.py` | `test_an_open_portal_is_warned_about_and_not_started_again` |  |  | An open portal is warned about and not started again. |
| `test_local.py` | `test_a_wiki_is_served_and_opens_once_it_is_up` |  |  | A wiki is served and opens once it is up. |
| `test_local.py` | `test_the_wiki_on_the_network` |  |  | The wiki on the network. |
| `test_local.py` | `test_start_local_keeps_the_output_in_a_log` |  |  | Start local keeps the output in a log. |
| `test_local.py` | `test_instance_running_sees_a_listening_app_and_does_not_disturb_it` |  |  | Instance running sees a listening app and does not disturb it. |
| `test_local.py` | `test_this_checkouts_suite_has_its_apps_and_wiki` |  |  | This checkouts suite has its apps and wiki. |
| `test_main_window.py` | `test_the_icons_are_nexus_at_512_and_128_px` |  |  | The icons are nexus at 512 and 128 px. |
| `test_main_window.py` | `test_the_checkout_is_the_suite_with_its_development_apps` |  |  | The checkout is the suite with its development apps. |
| `test_main_window.py` | `test_the_window_lists_the_apps_then_the_suites_tools` |  | 0.1 s | The window lists the apps then the suites tools. |
| `test_main_window.py` | `test_a_click_on_an_app_starts_it_and_says_so` |  |  | A click on an app starts it and says so. |
| `test_main_window.py` | `test_a_click_on_a_tool_opens_its_dialog_on_the_suite` |  |  | A click on a tool opens its dialog on the suite. |
| `test_main_window.py` | `test_a_checkout_without_tools_or_apps` |  |  | A checkout without tools or apps. |
| `test_main_window.py` | `test_start_runs_the_apps_script_in_its_folder_with_a_log` |  |  | Start runs the apps script in its folder with a log. |
| `test_main_window.py` | `test_a_second_launch_opens_no_window` |  |  | A double-click on the Desktop icon starts the app twice: the second launch hands over to the first. |
| `test_main_window.py` | `test_a_click_on_the_header_icon_opens_the_suites_wiki` |  |  | A click on the header icon opens the suites wiki. |
| `test_replace.py` | `test_nobody_open` |  |  | Nobody open. |
| `test_replace.py` | `test_the_open_window_closes_when_asked_and_only_then` |  |  | The open window closes when asked and only then. |
| `test_replace.py` | `test_a_dashboard_that_does_not_answer_is_ended` |  | 0.9 s | A dashboard that does not answer is ended. |
| `test_tours.py` | `test_every_program_of_the_manifest_once_in_its_order` |  |  | Every program of the manifest once in its order. |
| `test_tours.py` | `test_the_commands_carry_the_options` |  |  | The commands carry the options. |
| `test_tours.py` | `test_a_size_other_than_1080p_is_passed_on_and_names_the_video` |  |  | --size goes to the scripts only for 1440p and 2160p, so an older checkout's scripts still run at 1080p; the video is then named as the scripts name it, -2160p before .mp4. |
| `test_tours.py` | `test_the_dialogs_record_at_the_chosen_size` |  | 0.1 s | The dialogs record at the chosen size. |
| `test_tours.py` | `test_the_apps_dialog_records_the_ticked_apps_one_after_another` |  |  | The apps dialog records the ticked apps one after another. |
| `test_tours.py` | `test_a_failed_run_is_named_and_the_next_one_still_runs` |  | 0.1 s | A failed run is named and the next one still runs. |
| `test_tours.py` | `test_stop_ends_the_recording_and_what_it_started` |  |  | Stop ends the recording and what it started. |
| `test_tours.py` | `test_the_portal_dialog_records_into_videos_with_the_wiki_copy_when_asked` |  |  | The portal dialog records into videos with the wiki copy when asked. |
| `test_tours.py` | `test_a_checkout_without_the_tour_scripts_gets_the_dialog_greyed_out` |  |  | Without record-tour.sh the dialog says so and records nothing. |

## dev/demo

32 tests in 3 files, 0.4 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_main_window.py` | `test_the_icons_are_nexus_at_512_and_128_px` |  |  | The icons are nexus at 512 and 128 px. |
| `test_main_window.py` | `test_window_starts_with_steps_and_no_unvalidated_release` |  |  | Window starts with steps and no unvalidated release. |
| `test_main_window.py` | `test_without_a_release_in_downloads_the_suite_in_the_checkout_is_used` |  |  | The real checkout: its portal/install.sh and portal/apps.toml, the optional apps of it. |
| `test_main_window.py` | `test_release_selection_prefers_system_overlay` |  |  | Release selection prefers system overlay. |
| `test_main_window.py` | `test_window_automatically_loads_release_found_in_downloads` |  |  | Window automatically loads release found in downloads. |
| `test_main_window.py` | `test_choose_a_folder_inside_a_suite_loads_the_suite` |  |  | Choose a folder inside a suite loads the suite. |
| `test_main_window.py` | `test_test_connection_shows_popup_if_obs_is_not_running` |  |  | Test connection shows popup if obs is not running. |
| `test_main_window.py` | `test_test_connection_sets_and_reports_recordings_folder` |  |  | Test connection sets and reports recordings folder. |
| `test_main_window.py` | `test_recent_recordings_uses_the_recordings_folder` |  |  | Recent recordings uses the recordings folder. |
| `test_main_window.py` | `test_open_recording_starts_inline_player` |  |  | Open recording starts inline player. |
| `test_main_window.py` | `test_start_hides_window_and_global_shortcut_stops_recording` |  |  | Start hides window and global shortcut stops recording. |
| `test_main_window.py` | `test_a_second_launch_opens_no_window` |  |  | A double-click on the Desktop icon starts the app twice: the second launch hands over to the first. |
| `test_shortcut_service.py` | `test_shortcut_service_creates_session_binds_key_and_forwards_activation` |  |  | Shortcut service creates session binds key and forwards activation. |
| `test_workflow.py` | `test_manifest_lists_optional_apps_and_excludes_required_default` |  |  | Manifest lists optional apps and excludes required default. |
| `test_workflow.py` | `test_invalid_portal_release_is_rejected` |  |  | Invalid portal release is rejected. |
| `test_workflow.py` | `test_validate_release_accepts_suite_checkout_and_tool_folder` |  |  | Validate release accepts suite checkout and tool folder. |
| `test_workflow.py` | `test_find_portal_release_selects_newest_valid_folder` |  |  | Find portal release selects newest valid folder. |
| `test_workflow.py` | `test_find_portal_release_returns_none_for_missing_downloads` |  |  | Find portal release returns none for missing downloads. |
| `test_workflow.py` | `test_downloads_dir_respects_xdg_download_dir` |  |  | Downloads dir respects xdg download dir. |
| `test_workflow.py` | `test_validate_release_and_detect_installed_paths` |  |  | Validate release and detect installed paths. |
| `test_workflow.py` | `test_launch_installer_uses_terminal_and_returns_exit_marker` |  |  | Launch installer uses terminal and returns exit marker. |
| `test_workflow.py` | `test_recording_helpers_surface_server_errors` |  |  | Recording helpers surface server errors. |
| `test_workflow.py` | `test_set_recording_directory_configures_obs_folder` |  |  | Set recording directory configures obs folder. |
| `test_workflow.py` | `test_set_recording_directory_reports_obs_request_failure` |  |  | Set recording directory reports obs request failure. |
| `test_workflow.py` | `test_recent_recordings_returns_newest_video_files` |  |  | Recent recordings returns newest video files. |
| `test_workflow.py` | `test_recent_recordings_surfaces_unreadable_folder` |  |  | Recent recordings surfaces unreadable folder. |
| `test_workflow.py` | `test_start_recording_trusts_successful_obs_request_without_immediate_status_check` |  |  | Start recording trusts successful obs request without immediate status check. |
| `test_workflow.py` | `test_start_recording_reports_obs_request_failure` |  |  | Start recording reports obs request failure. |
| `test_workflow.py` | `test_stop_recording_trusts_successful_obs_request_without_immediate_status_check` |  |  | Stop recording trusts successful obs request without immediate status check. |
| `test_workflow.py` | `test_stop_recording_reports_obs_request_failure` |  |  | Stop recording reports obs request failure. |
| `test_workflow.py` | `test_connect_obs_converts_websocket_timeout_to_user_error` |  |  | Connect obs converts websocket timeout to user error. |
| `test_workflow.py` | `test_connect_obs_reports_when_obs_is_not_running` |  |  | Connect obs reports when obs is not running. |

## dev/deps

102 tests in 6 files, 2.1 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_bazzite.py` | `test_the_owners_board_up_to_date` |  |  | The running image first, the previous one kept for a rollback: nothing waits. |
| `test_bazzite.py` | `test_an_update_waits_for_a_reboot` |  |  | An update waits for a reboot. |
| `test_bazzite.py` | `test_a_rollback_is_not_an_update` |  |  | A rollback is not an update. |
| `test_bazzite.py` | `test_the_updater_failed_or_stopped_running` |  |  | The updater failed or stopped running. |
| `test_bazzite.py` | `test_not_bazzite_or_rpm_ostree_failing` |  |  | Not bazzite or rpm ostree failing. |
| `test_bazzite.py` | `test_only_reads` |  |  | rpm-ostree status and systemctl show: nothing that changes the system. |
| `test_bazzite.py` | `test_a_flattened_image_reads_os_release_and_never_runs_rpm_ostree` |  |  | A PS5 image (19-11-2026): no /run/ostree-booted, rpm-ostree refuses; the version is os-release's. |
| `test_bazzite.py` | `test_os_release_versions` |  |  | Os release versions. |
| `test_dependencies.py` | `test_catalog_lists_python_and_external_dependencies` |  |  | Catalog lists python and external dependencies. |
| `test_dependencies.py` | `test_app_has_the_standard_layout` |  |  | A Nexus app in dev/deps, its catalog per suite (owner, 07-11-2026: the suite's Dependency Checker moved here). |
| `test_dependencies.py` | `test_catalog_matches_all_runtime_requirement_manifests` |  |  | Catalog matches all runtime requirement manifests. |
| `test_dependencies.py` | `test_catalog_apps_match_the_portal_manifest` |  |  | Names and launchers come from portal/apps.toml (name, detect), so an installed app is found. |
| `test_dependencies.py` | `test_every_tool_names_its_need_and_root` |  |  | Every tool names its need and root. |
| `test_dependencies.py` | `test_external_tool_catalog_covers_app_specific_tools` |  |  | External tool catalog covers app specific tools. |
| `test_dependencies.py` | `test_catalog_tools_are_used_by_the_apps_that_list_them` |  |  | Catalog tools are used by the apps that list them. |
| `test_dependencies.py` | `test_unknown_owner_and_need_are_catalog_errors` |  |  | Unknown owner and need are catalog errors. |
| `test_dependencies.py` | `test_launcher_python_reads_the_exec_line` |  |  | Launcher python reads the exec line. |
| `test_dependencies.py` | `test_installed_environments_follow_each_launcher` |  |  | Installed environments follow each launcher. |
| `test_dependencies.py` | `test_environment_versions_read_site_packages` |  |  | Environment versions read site packages. |
| `test_dependencies.py` | `test_environment_versions_read_lib64_too` |  |  | Fedora's Python 3.15 keeps lib64/ apart from lib/: a compiled package (PyQt6) is in lib64/, pip in lib/. |
| `test_dependencies.py` | `test_packages_are_checked_in_each_app_environment` |  |  | A package of an app with its own venv is found there, not reported missing from the shared one. |
| `test_dependencies.py` | `test_packages_of_apps_that_are_not_installed_are_not_needed` |  |  | Packages of apps that are not installed are not needed. |
| `test_dependencies.py` | `test_package_version_that_misses_the_requirement_is_reported` |  |  | Two apps in one venv that ask differently (this suite's apps all ask the same of a package). |
| `test_dependencies.py` | `test_package_checks_preserve_independent_results` |  |  | Package checks preserve independent results. |
| `test_dependencies.py` | `test_satisfies` | 10 |  | Satisfies. |
| `test_dependencies.py` | `test_tool_check_reports_path` |  |  | Tool check reports path. |
| `test_dependencies.py` | `test_tools_are_found_in_the_apps_extra_folders` |  |  | A launch from the menu may lack ~/.local/bin on PATH; the apps look there anyway. |
| `test_dependencies.py` | `test_either_speed_test_will_do` |  |  | Either speed test will do. |
| `test_dependencies.py` | `test_flashrom_check_requires_internal_programmer` | 2 |  | Flashrom check requires internal programmer. |
| `test_dependencies.py` | `test_latest_pypi_version_uses_project_json` |  |  | Latest pypi version uses project json. |
| `test_dependencies.py` | `test_bad_pypi_response_is_an_explicit_check_error` |  |  | Bad pypi response is an explicit check error. |
| `test_dependencies.py` | `test_known_vulnerabilities_merge_aliases_and_link_the_cve` |  |  | OSV.dev has a GHSA and a PYSEC entry for one CVE: shown once, under the CVE ID, linked to Snyk. |
| `test_dependencies.py` | `test_no_known_vulnerabilities` |  |  | No known vulnerabilities. |
| `test_dependencies.py` | `test_vulnerabilities_are_checked_once_per_installed_version` |  |  | Vulnerabilities are checked once per installed version. |
| `test_dependencies.py` | `test_a_failed_vulnerability_check_is_not_reported_as_clean` |  |  | A failed vulnerability check is not reported as clean. |
| `test_dependencies.py` | `test_ffmpeg_is_asked_of_remote_plays_native_core` | 3 |  | Ffmpeg is asked of remote plays native core. |
| `test_dependencies.py` | `test_ffmpeg_not_found_without_the_app_or_its_core` |  |  | Ffmpeg not found without the app or its core. |
| `test_dependencies.py` | `test_remote_play_lists_the_ffmpeg_in_its_native_core` |  |  | Its python is where the installer puts the app's venv, and the probe asks the core the app imports. |
| `test_dependencies.py` | `test_too_old_only_when_a_newer_version_would_do` | 8 |  | Too old only when a newer version would do. |
| `test_dependencies.py` | `test_environment_needs_update` |  |  | Environment needs update. |
| `test_fixes.py` | `test_nothing_broken_needs_no_fix` |  |  | Nothing broken needs no fix. |
| `test_fixes.py` | `test_missing_and_outdated_packages_go_into_their_own_venv` |  |  | Missing and outdated packages go into their own venv. |
| `test_fixes.py` | `test_a_missing_required_tool_comes_from_homebrew_first_then_rpm_ostree` |  |  | A missing required tool comes from homebrew first then rpm ostree. |
| `test_fixes.py` | `test_optional_and_unfixable_tools_stay_out` |  |  | Optional and unfixable tools stay out. |
| `test_fixes.py` | `test_every_tool_names_at_most_one_formula_and_package` |  |  | Every tool names at most one formula and package. |
| `test_fixes.py` | `test_the_reminder_says_what_needs_the_user` |  |  | The reminder says what needs the user. |
| `test_fixes.py` | `test_the_notification_waits_for_a_button` |  |  | The notification waits for a button. |
| `test_fixes.py` | `test_remind_opens_the_app_on_a_click` |  |  | Remind opens the app on a click. |
| `test_fixes.py` | `test_an_empty_plan_is_false` |  |  | An empty plan is false. |
| `test_fixes.py` | `test_the_machines_updates_alone_make_a_notification_with_fix` |  |  | The hourly timer's sources are Nexus Deps' since 09-11-2026: Homebrew's updates alone are worth a word. |
| `test_fixes.py` | `test_a_flattened_image_installs_with_dnf_and_a_checkbox_per_package` |  |  | No ostree (a PS5 image): the Fedora package with dnf through pkexec, there at once, no rpm-ostree. |
| `test_fixes.py` | `test_chosen_keeps_the_checked_packages_and_a_kernel_restarts` |  |  | Chosen keeps the checked packages and a kernel restarts. |
| `test_system.py` | `test_every_source_with_its_updates_and_its_step` |  |  | Every source with its updates and its step. |
| `test_system.py` | `test_everything_current` |  |  | Everything current. |
| `test_system.py` | `test_a_venv_left_on_an_older_python_says_so` |  |  | Bazzite's image moved python3 to 3.15: the venv's python follows it, without the packages it had for 3.14. |
| `test_system.py` | `test_sources_this_machine_lacks_are_left_out` |  |  | Sources this machine lacks are left out. |
| `test_system.py` | `test_a_source_that_fails_says_why_and_offers_nothing` |  |  | A source that fails says why and offers nothing. |
| `test_system.py` | `test_homebrew_off_the_path_is_still_found` |  |  | A timer's service has no Homebrew on its PATH: Bazzite's own place is looked at. |
| `test_system.py` | `test_the_parsers_keep_to_what_the_tools_print` |  |  | The parsers keep to what the tools print. |
| `test_system.py` | `test_a_new_fedora_release_is_not_installed_by_a_click` |  |  | 44 → 45 changed the system's Python under the venv on 09-11-2026: such an image has the steps, not a step. |
| `test_system.py` | `test_major_versions_are_named` |  |  | Major versions are named. |
| `test_system.py` | `test_every_source_says_what_update_does` |  |  | Every source says what update does. |
| `test_system.py` | `test_dnf_lists_the_updates_with_the_kernel_and_its_restart` |  |  | Dnf lists the updates with the kernel and its restart. |
| `test_system.py` | `test_dnf_with_nothing_newer_or_failing` |  |  | Dnf with nothing newer or failing. |
| `test_system.py` | `test_a_flattened_image_has_dnf_instead_of_the_image` |  |  | A flattened image has dnf instead of the image. |
| `test_upstreams.py` | `test_the_catalog_is_in_sync_with_the_apps` |  |  | The pins, repos, names and launchers are the apps' own: dev/deps/run.sh --sync-upstreams fixes this. |
| `test_upstreams.py` | `test_every_app_with_a_pinned_upstream_is_listed` |  |  | Every app with a pinned upstream is listed. |
| `test_upstreams.py` | `test_the_constants_are_read_without_running_the_module` |  |  | The constants are read without running the module. |
| `test_upstreams.py` | `test_a_moved_pin_makes_the_catalog_stale` |  | 0.1 s | A moved pin makes the catalog stale. |
| `test_upstreams.py` | `test_an_emulator_at_its_pin_with_nothing_newer` |  |  | An emulator at its pin with nothing newer. |
| `test_upstreams.py` | `test_installed_behind_the_pin_and_upstream_past_it` |  |  | Installed behind the pin and upstream past it. |
| `test_upstreams.py` | `test_an_app_without_its_program_is_no_update` |  |  | An app without its program is no update. |
| `test_upstreams.py` | `test_github_offline` |  |  | Github offline. |
| `test_upstreams.py` | `test_the_comparisons` |  |  | The comparisons. |
| `test_upstreams.py` | `test_sonys_firmware_is_news_once` |  |  | The first look learns the versions; a later one names what changed; the one after says nothing again. |
| `test_upstreams.py` | `test_the_ps4_list_is_read_by_its_one_attribute` |  |  | The ps4 list is read by its one attribute. |
| `test_upstreams.py` | `test_devices_with_no_list_say_where_to_look` |  |  | Devices with no list say where to look. |
| `test_upstreams.py` | `test_the_reminder_names_an_upstream_once` |  |  | The reminder names an upstream once. |
| `test_upstreams.py` | `test_github_is_asked_signed_in` |  |  | Without a sign-in GitHub allows 60 requests an hour for the whole address, which the checks of a morning use up (owner, 14-11-2026: every card said "HTTP Error 403: rate limit exceeded"). |
| `test_upstreams.py` | `test_the_token_is_gh_s_and_only_for_github` |  |  | The token is gh s and only for github. |
| `test_window.py` | `test_window_displays_package_and_tool_results` |  | 0.1 s | Window displays package and tool results. |
| `test_window.py` | `test_missing_package_in_an_app_environment_is_reported` |  | 0.1 s | Missing package in an app environment is reported. |
| `test_window.py` | `test_tools_that_need_root_say_so` |  | 0.1 s | Tools that need root say so. |
| `test_window.py` | `test_about_popup_describes_the_purpose` |  | 0.1 s | About popup describes the purpose. |
| `test_window.py` | `test_cve_marks` |  | 0.1 s | Cve marks. |
| `test_window.py` | `test_missing_tools_advise_what_they_are_needed_for` |  | 0.1 s | Missing tools advise what they are needed for. |
| `test_window.py` | `test_needs_update_when_an_app_wants_newer_or_a_release_fixes_a_vulnerability` |  | 0.1 s | Needs update when an app wants newer or a release fixes a vulnerability. |
| `test_window.py` | `test_the_bazzite_card_on_top` |  | 0.1 s | An update waiting for a reboot: the card says so first, in the system section above the packages. |
| `test_window.py` | `test_the_bazzite_card_without_bazzite` |  | 0.1 s | The bazzite card without bazzite. |
| `test_window.py` | `test_fix_is_off_until_there_is_something_to_fix` |  | 0.2 s | Fix is off until there is something to fix. |
| `test_window.py` | `test_fix_asks_with_every_command_and_no_changes_nothing` |  | 0.1 s | Fix asks with every command and no changes nothing. |
| `test_window.py` | `test_fix_offered_at_once_with_fix` |  | 0.1 s | --fix: the notification's Fix… button asks as soon as the check is done, once. |
| `test_window.py` | `test_the_question_names_a_restart_and_what_fix_leaves` |  |  | The question names a restart and what fix leaves. |
| `test_window.py` | `test_the_fix_dialog_runs_the_steps_and_stops_at_a_failure` |  |  | The fix dialog runs the steps and stops at a failure. |
| `test_window.py` | `test_the_machines_updates_have_a_card_each` |  | 0.1 s | Every update system wide is shown (09-11-2026: the hourly notice named updates the window did not). |
| `test_window.py` | `test_a_cards_update_asks_for_its_own_step_alone` |  | 0.1 s | A cards update asks for its own step alone. |
| `test_window.py` | `test_fix_offered_for_the_machines_updates_alone` |  | 0.1 s | --fix from a notification about Homebrew alone: the question comes once both checks are done. |
| `test_window.py` | `test_an_image_of_a_new_fedora_release_is_by_hand` |  | 0.1 s | A system-wide change has no Update: the card says why, and its i gives the steps. |
| `test_window.py` | `test_the_emulators_and_firmware_have_a_section_of_their_own` |  | 0.1 s | The emulators and firmware have a section of their own. |
| `test_window.py` | `test_the_question_has_a_checkbox_per_package` |  |  | Only what stays checked is updated (owner, 19-11-2026: "no checkmark, no update/install"). |
| `test_window.py` | `test_the_question_for_dnf_names_pkexec_and_the_kernels_restart` |  |  | The question for dnf names pkexec and the kernels restart. |
| `test_window.py` | `test_a_dnf_card_updates_the_checked_packages_alone` |  |  | A dnf card updates the checked packages alone. |

## dev/itests

15 tests in 1 files, 0.3 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_runner.py` | `test_discovery_excludes_the_helpers_and_takes_the_bash_scripts` |  |  | Discovery excludes the helpers and takes the bash scripts. |
| `test_runner.py` | `test_a_script_runs_with_bash` |  |  | A script runs with bash. |
| `test_runner.py` | `test_the_suites_tests_are_in_its_tools` |  |  | The suites tests are in its tools. |
| `test_runner.py` | `test_runner_adds_homebrew_fakeroot_directory_to_path` |  |  | Runner adds homebrew fakeroot directory to path. |
| `test_runner.py` | `test_runner_process_can_find_fakeroot_from_homebrew` |  |  | Runner process can find fakeroot from homebrew. |
| `test_runner.py` | `test_runner_executes_selected_tests_in_order_and_continues_after_failure` |  |  | Runner executes selected tests in order and continues after failure. |
| `test_runner.py` | `test_runner_rejects_helpers_and_scripts_outside_the_tests_folder` |  |  | Runner rejects helpers and scripts outside the tests folder. |
| `test_runner.py` | `test_window_lists_the_suites_tests` |  |  | Window lists the suites tests. |
| `test_runner.py` | `test_window_on_the_real_checkout_lists_the_suites_installer_tests` |  |  | Window on the real checkout lists the suites installer tests. |
| `test_runner.py` | `test_a_checkout_without_tests_says_so` |  |  | A checkout without tests says so. |
| `test_runner.py` | `test_window_shows_green_check_and_red_cross_at_row_end` |  |  | Window shows green check and red cross at row end. |
| `test_runner.py` | `test_window_keeps_previous_results_when_another_test_starts` |  |  | Window keeps previous results when another test starts. |
| `test_runner.py` | `test_cancel_stops_the_current_test_and_skips_queued_tests` |  | 0.1 s | Cancel stops the current test and skips queued tests. |
| `test_runner.py` | `test_installer_creates_desktop_entries_and_uninstalls_only_them` |  | 0.1 s | Installer creates desktop entries and uninstalls only them. |
| `test_runner.py` | `test_a_second_launch_opens_no_window` |  |  | A double-click on the Desktop icon starts the app twice: the second launch hands over to the first. |

## dev/nrt

123 tests in 4 files, 23.1 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_command_line.py` | `test_plain_drops_colours_and_progress_returns` |  |  | Plain drops colours and progress returns. |
| `test_command_line.py` | `test_the_commands_a_step_shows` |  |  | Retract's block: its commands without the comments; a # inside quotes is part of the command. |
| `test_command_line.py` | `test_commands_offered_go_on_the_line_not_run` |  |  | Commands offered go on the line not run. |
| `test_command_line.py` | `test_the_board_checks_go_to_a_terminal` |  |  | check-release.sh asks for the sudo password and keeps the portal running, which the line cannot do (owner, 03-11-2026: run here, sudo asked through KDE's dialog at every one of the installer's 14 calls). |
| `test_command_line.py` | `test_without_bash_it_says_so` |  |  | Without bash it says so. |
| `test_command_line.py` | `test_runs_in_the_checkout_and_streams_the_output` |  | 0.1 s | Runs in the checkout and streams the output. |
| `test_command_line.py` | `test_cd_carries_over_and_a_failure_shows_its_code` |  | 0.2 s | Cd carries over and a failure shows its code. |
| `test_command_line.py` | `test_nothing_waits_for_input` |  | 0.1 s | Input is closed and git asks nothing: a read ends at once, git commit without -m names the way out. |
| `test_command_line.py` | `test_stop_interrupts_the_command_and_what_it_started` |  | 0.1 s | Ctrl+C ends the command; a job it started in the background (which ignores Ctrl+C in a script) ends too. |
| `test_command_line.py` | `test_clear_empties_the_output` |  | 0.1 s | Clear empties the output. |
| `test_command_line.py` | `test_history_with_up_and_down_kept_in_the_settings` |  |  | History with up and down kept in the settings. |
| `test_command_line.py` | `test_run_now_runs_a_button_command` |  | 0.1 s | The window's git buttons: their command runs as if typed (in the history too), not while another runs; how it ended is kept, so a commit's message goes only when it passed. |
| `test_command_line.py` | `test_every_command_and_its_output_are_logged` |  | 0.1 s | Every command and its output are logged. |
| `test_flow.py` | `test_the_release_runs_on_github_through_release_yml` |  |  | The release runs on github through release yml. |
| `test_flow.py` | `test_the_release_holds_the_changed_app_and_its_portal` |  | 0.1 s | The release holds the changed app and its portal. |
| `test_flow.py` | `test_nothing_changed_nothing_to_release` |  | 0.1 s | Nothing changed nothing to release. |
| `test_flow.py` | `test_a_portal_bump_with_nothing_else_is_nothing_to_release` |  | 0.2 s | Only the version and its Release entry moved since the tags (owner, 15-11-2026: Bump wrote portal 21.0.2 while 21.0.1 waited for its device test, and Start released it, a second portal of the same apps). |
| `test_flow.py` | `test_a_version_copy_that_moved_with_something_else_still_counts` |  | 0.1 s | A version copy that moved with something else still counts. |
| `test_flow.py` | `test_a_withdrawal_entry_is_no_release_of_the_app` |  | 0.1 s | Retract writes a Withdrawn: entry in the app's CHANGELOG: the app ships nothing new, its portal does. |
| `test_flow.py` | `test_start_writes_the_release_as_steps_one_and_two_would` |  | 0.1 s | Start writes the release as steps one and two would. |
| `test_flow.py` | `test_a_typed_version_overrides_the_suggestion` |  | 0.1 s | A typed version overrides the suggestion. |
| `test_flow.py` | `test_a_portal_typed_too_low_gets_what_ci_asks` |  | 0.1 s | A portal typed too low gets what ci asks. |
| `test_flow.py` | `test_wrong_versions_are_refused_before_anything_is_written` |  | 0.1 s | Wrong versions are refused before anything is written. |
| `test_flow.py` | `test_start_needs_a_clean_tree_at_the_last_push` |  | 0.1 s | Start needs a clean tree at the last push. |
| `test_flow.py` | `test_the_one_command_commits_pushes_and_starts_the_workflow` |  |  | The one command commits pushes and starts the workflow. |
| `test_flow.py` | `test_the_run_is_followed_stopped_and_resumed` |  |  | The run is followed stopped and resumed. |
| `test_flow.py` | `test_the_device_test_and_publish_work_on_the_portals_draft` |  |  | The device test and publish work on the portals draft. |
| `test_flow.py` | `test_a_release_commit_whose_push_stopped_is_pushed_and_started` |  | 0.1 s | A release commit whose push stopped is pushed and started. |
| `test_flow.py` | `test_the_window_opens_on_the_nexus_release` |  | 0.4 s | The window opens on the nexus release. |
| `test_flow.py` | `test_the_suite_field_has_room_before_its_text_and_only_it` |  | 0.4 s | The suite field has room before its text and only it. |
| `test_flow.py` | `test_start_writes_the_release_and_runs_the_one_command` |  | 0.4 s | Start writes the release and runs the one command. |
| `test_flow.py` | `test_start_fetches_the_tags_and_main_first_and_goes_on` |  | 0.7 s | A portal is tagged on GitHub when it is published, and a release pins on main after it: neither is here until fetched (owner, 31-10-2026: Release 6.2.0 again after 6.2.0 was out; the Pin ... |
| `test_flow.py` | `test_fetch_tags_names_a_tag_here_that_git_will_not_move` |  | 0.1 s | A tag here on another commit than GitHub's: git refuses to move it ("would clobber existing tag"), and the message says which tag and what to do (owner, 03-11-2026: Start only said the fetch failed). |
| `test_flow.py` | `test_start_shows_why_the_fetch_failed` |  | 0.5 s | Start shows why the fetch failed. |
| `test_flow.py` | `test_catch_up_brings_in_mains_commits_under_this_checkouts` |  | 0.2 s | Catch up brings in mains commits under this checkouts. |
| `test_flow.py` | `test_a_version_only_offered_follows_the_next_offer` |  | 0.6 s | After the tags are read again the table offers anew; what the owner typed stays (owner, 31-10-2026: the old offer 5.3.0 stayed as if typed, and Start refused it). |
| `test_flow.py` | `test_changes_not_committed_make_commit_the_step_to_do` |  | 0.7 s | The steps in their order (owner, 30-10-2026: "exactly what has to be done in their logical sequence"): with changes in the tree, step 2 Commit is the one lit, and Start waits. |
| `test_flow.py` | `test_the_step_to_do_follows_the_release` |  |  | Every step in turn: pull, commit, push, CI, Start, the run, the device test and Publish, the pin commit. |
| `test_flow.py` | `test_a_failed_release_gets_its_fix_then_starts_again_on_it` |  |  | CI failed on the release commit (30-10-2026): the release is written and pushed, so its fix goes through Commit, Push and CI, then the run starts again on it; Start never writes it a second time. |
| `test_flow.py` | `test_a_failed_release_run_lasts_with_fixes_on_top` |  | 0.1 s | A failed release run lasts with fixes on top. |
| `test_flow.py` | `test_failed_ci_runs_again` |  | 0.5 s | CI failed for GitHub's own trouble (30-10-2026, Actions degraded): step 4 lights Run CI again, which starts the failed CI runs of HEAD again; a passed one and another commit's are left alone. |
| `test_flow.py` | `test_ci_state_reads_the_ci_runs_of_the_commit` |  |  | Ci state reads the ci runs of the commit. |
| `test_flow.py` | `test_the_release_run_lasts_until_other_work_is_committed` |  | 0.1 s | The release run lasts until other work is committed. |
| `test_flow.py` | `test_a_release_with_a_draft_to_test_lasts_with_other_work_on_top` |  | 0.1 s | Other work pushed before a portal draft's device test (owner, 04-11-2026): the release lasts until the draft is published or Not OK, so Start never replaces it. |
| `test_flow.py` | `test_a_portal_version_raised_after_a_published_release_is_the_next_release` |  | 0.1 s | The portal's version raised in a commit after its release was published (owner, 07-11-2026: NRT showed the release on GitHub done and offered the device test of ps5-portal-v10.1.0, a draft no run had built): the run's own portal is out, so that release is over and Start new release is next; the draft is read at the run's commit. |
| `test_flow.py` | `test_a_push_git_has_not_fetched_lights_the_pull` |  | 0.4 s | The release's Pin ... |
| `test_flow.py` | `test_the_device_test_and_publish` |  | 0.5 s | The device test and publish. |
| `test_flow.py` | `test_the_portal_choice_holds_only_the_drafts` |  | 0.4 s | A tag published since the choice was filled leaves it (owner, 05-11-2026: the choice stayed on portal-v15.2.0, so Publish published it again): only the draft is left. |
| `test_flow.py` | `test_not_ok_is_the_runs_and_a_fix_goes_on_from_commit` |  |  | Not ok is the runs and a fix goes on from commit. |
| `test_flow.py` | `test_commit_offers_the_portal_bump_when_apps_toml_changed` |  | 1.2 s | apps.toml changed since the last portal release (an app added): the commit's manifest check would refuse the commit, so Commit offers the portal bump (owner, 02-11-2026) and writes it with its CHANGELOG entry on a yes; on a no nothing is committed and the output says why. |
| `test_flow.py` | `test_the_step_being_done_says_a_command_runs` |  | 0.5 s | While its command runs (owner, 05-11-2026: Push stayed lit for its two minutes of CI's jobs, which read as "push again"), the step to do has a teal ⋯ and says what runs, and its pill rests. |
| `test_flow.py` | `test_ci_here_is_read_from_its_output` |  |  | The Push step's tools/ci-local.sh (owner, 15-11-2026: the push seemed to hang, a failed job went unseen). |
| `test_flow.py` | `test_a_run_asked_to_run_again_is_not_asked_twice` |  |  | A run asked to run again is not asked twice. |
| `test_flow.py` | `test_why_a_push_ended_badly` |  |  | Why a push ended badly. |
| `test_flow.py` | `test_the_push_shows_ci_here_and_a_failure_stays_on_its_step` |  | 0.8 s | The push shows ci here and a failure stays on its step. |
| `test_flow.py` | `test_a_push_github_has_no_runs_of_yet_shows_no_old_failure` |  | 0.4 s | Right after a push, GitHub's newest runs are the commit's before: one that failed showed this push as failed until GitHub had started its runs (owner, 15-11-2026). |
| `test_flow.py` | `test_the_portal_video_check` |  |  | tools/portal_tour.py --check: "" when the video is current or the suite has none, else why it waits. |
| `test_main_window.py` | `test_every_widget_keeps_qts_window_method` |  | 0.4 s | An attribute named window on a widget hides QWidget.window(), which the suite's tooltip calls on the widget it is shown for: hovering the build indicator stopped the app that way. |
| `test_main_window.py` | `test_without_notify_send_the_tray_icon_notifies` |  | 0.3 s | A desktop without notify-send: the notification comes from the tray icon instead (owner, 28-10-2026). |
| `test_main_window.py` | `test_tooltip_over_the_build_indicator` |  | 0.4 s | Tooltip over the build indicator. |
| `test_main_window.py` | `test_the_header_is_a_row_of_pills` |  | 0.4 s | Refresh, GitHub's build, its API requests left and GitHub status: pills as in the apps' headers, all as wide as the widest (owner, 20-10-2026). |
| `test_main_window.py` | `test_selection_is_a_teal_outline` |  | 0.4 s | A selected cell and the focused input field: a rounded outline in Nexus's teal on a transparent background, not the desktop's solid highlight (rendered: the cell's middle keeps the table's own background). |
| `test_main_window.py` | `test_a_second_launch_opens_no_window` |  |  | A double-click on the Desktop icon starts the app twice: the second launch hands over to the first. |
| `test_main_window.py` | `test_the_settings_of_the_earlier_name_are_taken_over` |  |  | Nexus Releases' settings (nexus-releases, until 30-10-2026) become the Nexus Release Tool's, once. |
| `test_main_window.py` | `test_own_settings_are_never_replaced` |  |  | Own settings are never replaced. |
| `test_main_window.py` | `test_one_output_tab` |  | 0.4 s | Commands, the command line with its output, is the one output tab after the steps (owner, 01-11-2026: the Logs tab was mostly empty): what a step writes shows there under a line that names the step, and Commands opens when the step that wrote is the tab open (not for Remove suite, whose lines come while you click). |
| `test_main_window.py` | `test_a_step_offers_its_commands` |  | 0.3 s | A step offers its commands. |
| `test_main_window.py` | `test_github_status_is_read_from_the_status_page` |  |  | Github status is read from the status page. |
| `test_main_window.py` | `test_github_status_is_a_pill_that_opens_the_status_page` |  | 0.3 s | Green while GitHub is up, red while githubstatus.com reports a problem, gray while not known; a click opens https://www.githubstatus.com/ (owner, 19-10-2026). |
| `test_main_window.py` | `test_claude_usage_counts_each_answer_once` |  |  | Today's tokens and the last 5 hours' from Claude Code's transcripts, subagents' included; an answer of several parts counts once, Claude Code's own notes (<synthetic>) and other lines not at all. |
| `test_main_window.py` | `test_claude_usage_is_a_pill_that_opens_the_usage_page` |  | 0.4 s | Claude tokens today (the blue edge every neutral pill has, owner 26-10-2026), hidden without Claude Code; a click opens Claude's usage page. |
| `test_main_window.py` | `test_the_window_has_nexus_design` |  | 0.4 s | A Nexus app, not a suite's (owner, 26-10-2026): create_app() puts Nexus's theme on the application (ink, silver, teal: nexus/docs/stylesheets/nexus.css), the widgets draw with it, and the icon is the Nexus drawing. |
| `test_main_window.py` | `test_the_icons_are_the_nexus_drawing` |  |  | The app's icon and its menu icon are the Nexus drawing at 512 and 128 px, square. |
| `test_main_window.py` | `test_remove_suite_runs_check_release_remove_on_the_board` |  | 0.4 s | Remove suite (owner, 15-11-2026): check-release.sh remove in a terminal, on the board. |
| `test_main_window.py` | `test_an_old_portal_video_holds_the_release` |  | 0.6 s | An orange banner with Record new video now while the wiki's Portal Tour is older than the portal, and Start new release off until it is recorded (owner, 15-11-2026). |
| `test_plan.py` | `test_a_suites_tags_carry_its_prefix` |  | 0.1 s | The suite's TAG_PREFIX starts its tags: the apps' and the portal's, never core's; a tag without it is not the suite's. |
| `test_plan.py` | `test_units` |  | 0.1 s | Units. |
| `test_plan.py` | `test_versions` |  |  | Versions. |
| `test_plan.py` | `test_set_version_changes_a_copy_with_a_comment` |  | 0.1 s | Set version changes a copy with a comment. |
| `test_plan.py` | `test_set_version_changes_every_copy_but_tests` |  | 0.1 s | Set version changes every copy but tests. |
| `test_plan.py` | `test_amsterdam_time` | 5 |  | Amsterdam time. |
| `test_plan.py` | `test_changelog_entry` |  | 0.1 s | Changelog entry. |
| `test_plan.py` | `test_applying_a_release_again_keeps_one_entry` |  | 0.1 s | Apply after a check stopped the commit wrote "Release 1.3.0." a second time (owner, 28-10-2026): the same release replaces the newest entry, with the latest notes; another release, or another kind of entry, is added. |
| `test_plan.py` | `test_a_pushed_release_entry_stays` |  | 0.1 s | The portal release replaced the "Release 3.2.0. |
| `test_plan.py` | `test_pin_and_portal` |  | 0.1 s | Pin and portal. |
| `test_plan.py` | `test_ticker_shows_the_runs_of_the_push` |  | 0.2 s | The ticker shows every run of the newest push, the running ones first. |
| `test_plan.py` | `test_a_pushed_head_without_a_run_is_looked_at_again_soon` |  | 0.3 s | GitHub starts the CI of a push seconds after it (owner, 05-11-2026: CI ran on GitHub while the CI passes step said it had none, for 5 minutes): while the pushed HEAD has no run, the next look is in 10 s, not 5 minutes. |
| `test_plan.py` | `test_a_run_that_finishes_is_told_about` |  | 0.3 s | A run seen running that finishes gives a desktop notification, which names it. |
| `test_plan.py` | `test_git_button_commands` |  |  | Git button commands. |
| `test_plan.py` | `test_git_state` |  | 0.1 s | Git state. |
| `test_plan.py` | `test_window_get_up_to_date_counts_what_the_remote_has` |  | 0.5 s | Get up to date, the first step (owner, 28-10-2026: a push from the other machine only showed as a push that failed): its pill runs git pull, its line counts what the remote has that HEAD does not, and it is the step to do when GitHub's newest push on main is no commit here. |
| `test_plan.py` | `test_the_minimum_needs_no_second_bump_for_the_pins` |  | 0.2 s | The owner's case of 17-10-2026: the push with the apps' releases carried the portal bump; the next push, with their checksums pinned, was offered 1.13.1 (a patch over the last push). |
| `test_plan.py` | `test_withdrawal` |  | 0.1 s | Withdrawal. |
| `test_plan.py` | `test_needs_release_follows_what_ships` |  | 0.3 s | Needs release follows what ships. |
| `test_plan.py` | `test_core_and_manual_changes_count_for_the_apps_that_ship_them` |  | 0.1 s | Core and manual changes count for the apps that ship them. |
| `test_plan.py` | `test_core_bumped_with_its_change_needs_no_new_version` |  | 0.2 s | Core went to a new version with its change (released with some apps), and another app's release still carries it: that version already holds the change, so core offers itself as it is, not a higher one. |
| `test_plan.py` | `test_a_tag_before_the_bump_is_reported` |  | 0.2 s | A tag before the bump is reported. |
| `test_plan.py` | `test_window_warns_about_a_bad_tag` |  | 0.4 s | Window warns about a bad tag. |
| `test_plan.py` | `test_build_state_of_the_latest_push` |  |  | Build state of the latest push. |
| `test_plan.py` | `test_jobs_and_the_step_each_is_at` |  |  | Jobs and the step each is at. |
| `test_plan.py` | `test_window_ticker_shows_the_jobs_of_the_runs` |  | 0.3 s | Window ticker shows the jobs of the runs. |
| `test_plan.py` | `test_window_ticker_runs_a_failed_run_again` |  | 0.3 s | Run again in the ticker (owner, 06-11-2026): shown while a run of the newest push failed, it starts that run's failed jobs again; a run canceled for a later one of its workflow does not count. |
| `test_plan.py` | `test_fetch_runs_sends_the_etag` |  |  | Fetch runs sends the etag. |
| `test_plan.py` | `test_fetch_runs_follows_a_full_page_with_the_rest_of_heads_runs` |  |  | A release of 26 apps started 26 Release runs and as many index runs on its commit, so the page of 30 ended on that commit and the CI runs under them were never seen: the CI passes step never lit (owner, 04-11-2026). |
| `test_plan.py` | `test_github_token_from_the_environment_or_a_gh_login` |  |  | Github token from the environment or a gh login. |
| `test_plan.py` | `test_token_warning` |  |  | Token warning. |
| `test_plan.py` | `test_github_token_asked_once_while_checks_overlap` |  | 0.3 s | Github token asked once while checks overlap. |
| `test_plan.py` | `test_fetch_runs_signs_in_and_reports_the_limit` |  |  | Fetch runs signs in and reports the limit. |
| `test_plan.py` | `test_window_build_indicator_notifies_when_a_run_ends` |  | 0.5 s | Window build indicator notifies when a run ends. |
| `test_plan.py` | `test_title_names_the_checkouts_commit_and_date` |  | 0.3 s | No version: the tool is never released, so its header names the checkout's commit and its time. |
| `test_plan.py` | `test_window_withdraws` |  | 0.4 s | Window withdraws. |
| `test_plan.py` | `test_the_kind_of_change_sets_the_level` |  |  | The kind of change sets the level. |
| `test_plan.py` | `test_an_added_entry_since_the_tag_asks_for_a_minor_release` |  | 0.2 s | An added entry since the tag asks for a minor release. |
| `test_plan.py` | `test_counted_from_the_last_tag_not_a_bump_already_made` |  | 0.3 s | VERSION bumped to 0.1.1 (not tagged) and then a feature: 0.2.0 from alpha-v0.1.0 comes first. |
| `test_plan.py` | `test_a_core_change_counts_for_the_apps_that_carry_it` |  | 0.1 s | A core change counts for the apps that carry it. |
| `test_plan.py` | `test_a_first_release_is_offered_as_it_is` |  | 0.1 s | A first release is offered as it is. |
| `test_plan.py` | `test_the_portal_counts_apps_toml_since_its_last_tag` |  | 0.1 s | An app added to apps.toml and pushed before the portal release: the minimum (as check_manifest) and the suggestion both count it against the last portal tag, not the last push. |
| `test_plan.py` | `test_the_suites_names_and_icons` |  |  | The suite by its portal's name, with its portal's icon; the folder's name and no icon without them. |
| `test_plan.py` | `test_the_git_questions_are_asked_once_or_side_by_side` |  | 0.1 s | load_units() reads the tags and the untracked files once, and asks each unit's two questions side by side; the window's step 1 reads its CHANGELOGs at the tags with one git cat-file (owner, 27-10-2026: the window was slow, some 20 ms per git process). |
| `test_plan.py` | `test_read_blobs_reads_each_file_or_none` |  | 0.1 s | Read blobs reads each file or none. |
| `test_plan.py` | `test_git_answers_are_utf8_on_every_system` |  | 0.1 s | git() reads git's output as UTF-8, whatever the locale: another encoding garbled a CHANGELOG's é and ×, so step 1 counted every entry of such a CHANGELOG as new since the tag. |
| `test_plan.py` | `test_git_takes_no_optional_locks` |  |  | git() runs with GIT_OPTIONAL_LOCKS=0: the build pill's poll runs git status, which took .git/index.lock to refresh the index, and a poll during the Commands tab's git add -A or git commit made that fail. |
| `test_plan.py` | `test_push_brings_in_what_github_has_first` |  |  | The release's Pin ... |

## dev/sounds

22 tests in 2 files, 0.6 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_main_window.py` | `test_the_icons_are_nexus_at_512_and_128_px` |  |  | The icons are nexus at 512 and 128 px. |
| `test_main_window.py` | `test_the_window_starts_on_the_tick_and_plays_nothing_until_asked` |  |  | The window starts on the tick and plays nothing until asked. |
| `test_main_window.py` | `test_a_preset_sets_the_sliders_and_plays` |  |  | A preset sets the sliders and plays. |
| `test_main_window.py` | `test_a_slider_let_go_renders_the_custom_sound_and_plays_it` |  | 0.1 s | A slider let go renders the custom sound and plays it. |
| `test_main_window.py` | `test_the_try_buttons_play_when_the_focus_reaches_them_and_the_d_pad_moves_it` |  |  | The try buttons play when the focus reaches them and the d pad moves it. |
| `test_main_window.py` | `test_keep_awake_follows_the_box_and_is_remembered` |  |  | Keep awake follows the box and is remembered. |
| `test_main_window.py` | `test_the_sound_and_the_preset_are_remembered` |  |  | The sound and the preset are remembered. |
| `test_main_window.py` | `test_save_writes_the_wav_and_remembers_the_folder` |  |  | Save writes the wav and remembers the folder. |
| `test_main_window.py` | `test_without_an_output_the_window_says_so` |  |  | Without an output the window says so. |
| `test_main_window.py` | `test_the_wave_view_draws_without_frames_and_with_them` |  |  | The wave view draws without frames and with them. |
| `test_main_window.py` | `test_the_real_player_plays_a_file_of_its_own_per_sound_and_cleans_up` |  | 0.1 s | QSoundEffect keeps a loaded file by its address: each render gets a file of its own, the one before goes. |
| `test_main_window.py` | `test_main_parses_version` |  |  | Main parses version. |
| `test_synth.py` | `test_every_preset_renders_to_its_length_with_its_peak_at_its_volume` |  |  | Every preset renders to its length with its peak at its volume. |
| `test_synth.py` | `test_the_tick_is_the_demos_tick` |  |  | The default: a 1200 Hz sine, 50 ms, dying off with exp(-40 t), its peak at 80 %. |
| `test_synth.py` | `test_the_lead_in_is_silence_then_the_sound` |  |  | The lead in is silence then the sound. |
| `test_synth.py` | `test_more_tones_follow_each_an_interval_higher` |  |  | Two tones a fifth apart: the second has about 1.5 times the zero crossings of the first. |
| `test_synth.py` | `test_a_sweep_changes_the_pitch_over_the_tone` |  |  | A sweep changes the pitch over the tone. |
| `test_synth.py` | `test_every_waveform_renders_and_noise_has_no_phase` |  |  | Every waveform renders and noise has no phase. |
| `test_synth.py` | `test_zero_volume_or_zero_decay_still_render` |  |  | Zero volume or zero decay still render. |
| `test_synth.py` | `test_clamp_keeps_every_number_in_its_range_and_the_waveform_known` |  |  | Clamp keeps every number in its range and the waveform known. |
| `test_synth.py` | `test_values_round_trip_through_strings_as_the_settings_keep_them` |  |  | Values round trip through strings as the settings keep them. |
| `test_synth.py` | `test_write_wav_is_16_bit_mono_at_44100` |  |  | Write wav is 16 bit mono at 44100. |

## dev/studio

58 tests in 6 files.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_audio.py` | `test_another_rate_becomes_the_mixes_rate_with_the_same_sound` |  |  | Another rate becomes the mixes rate with the same sound. |
| `test_audio.py` | `test_going_down_drops_what_the_new_rate_cannot_hold` |  |  | Going down drops what the new rate cannot hold. |
| `test_audio.py` | `test_the_same_rate_and_an_empty_sound_stay_as_they_are` |  |  | The same rate and an empty sound stay as they are. |
| `test_audio.py` | `test_one_channel_goes_to_both_sides_and_more_than_two_lose_the_rest` |  |  | One channel goes to both sides and more than two lose the rest. |
| `test_audio.py` | `test_a_voice_file_loads_as_stereo_at_the_mixes_rate` |  |  | A voice file loads as stereo at the mixes rate. |
| `test_audio.py` | `test_what_is_no_sound_file_says_so` |  |  | What is no sound file says so. |
| `test_audio.py` | `test_every_format_is_written_and_read_back` |  |  | Every format is written and read back. |
| `test_audio.py` | `test_an_unknown_format_and_a_failed_write_leave_nothing` |  |  | An unknown format and a failed write leave nothing. |
| `test_audio.py` | `test_the_output_gets_16_bit_samples_that_never_wrap` |  |  | The output gets 16 bit samples that never wrap. |
| `test_audio.py` | `test_a_drawing_gets_the_lowest_and_highest_sample_of_each_part` |  |  | A drawing gets the lowest and highest sample of each part. |
| `test_main_window.py` | `test_the_icons_are_nexus_at_512_and_128_px` |  |  | The icons are nexus at 512 and 128 px. |
| `test_main_window.py` | `test_the_window_opens_on_the_warm_pad_without_a_voice` |  |  | The window opens on the warm pad without a voice. |
| `test_main_window.py` | `test_without_an_output_the_status_line_says_so` |  |  | Without an output the status line says so. |
| `test_main_window.py` | `test_a_preset_fills_the_controls_and_a_moved_control_says_custom` |  |  | A preset fills the controls and a moved control says custom. |
| `test_main_window.py` | `test_the_sliders_show_their_value_with_its_unit` |  |  | The sliders show their value with its unit. |
| `test_main_window.py` | `test_a_sound_file_becomes_the_voice` |  |  | A sound file becomes the voice. |
| `test_main_window.py` | `test_the_top_row_is_four_pills_of_one_width` |  |  | The top row is four pills of one width. |
| `test_main_window.py` | `test_without_a_voice_length_sets_how_long_the_mix_lasts` |  |  | Without a voice length sets how long the mix lasts. |
| `test_main_window.py` | `test_with_a_voice_length_is_lead_in_voice_and_tail_and_moving_it_sets_the_tail` |  |  | With a voice length is lead in voice and tail and moving it sets the tail. |
| `test_main_window.py` | `test_reset_puts_the_background_and_the_mix_on_their_defaults_and_keeps_the_voice` |  |  | Reset puts the background and the mix on their defaults and keeps the voice. |
| `test_main_window.py` | `test_the_open_dialog_remembers_its_folder_and_cancel_changes_nothing` |  |  | The open dialog remembers its folder and cancel changes nothing. |
| `test_main_window.py` | `test_what_is_no_sound_file_is_said_and_the_voice_stays` |  |  | What is no sound file is said and the voice stays. |
| `test_main_window.py` | `test_a_spoken_text_becomes_the_voice_and_cancel_changes_nothing` |  |  | A spoken text becomes the voice and cancel changes nothing. |
| `test_main_window.py` | `test_play_makes_the_mix_draws_it_and_plays_it` |  |  | Play makes the mix draws it and plays it. |
| `test_main_window.py` | `test_a_mix_is_made_again_only_after_a_change` |  |  | A mix is made again only after a change. |
| `test_main_window.py` | `test_a_mix_too_loud_says_it_was_turned_down` |  |  | A mix too loud says it was turned down. |
| `test_main_window.py` | `test_try_background_plays_it_alone_and_leaves_the_mix` |  |  | Try background plays it alone and leaves the mix. |
| `test_main_window.py` | `test_save_writes_the_mix_that_was_heard_without_making_it_again` |  |  | Save writes the mix that was heard without making it again. |
| `test_main_window.py` | `test_save_makes_the_mix_first_when_it_was_not_played` |  |  | Save makes the mix first when it was not played. |
| `test_main_window.py` | `test_the_save_dialog_offers_the_last_format_and_adds_the_suffix` |  |  | The save dialog offers the last format and adds the suffix. |
| `test_main_window.py` | `test_an_unknown_format_and_a_failed_write_are_said` |  |  | An unknown format and a failed write are said. |
| `test_main_window.py` | `test_the_remix_is_remembered` |  |  | The remix is remembered. |
| `test_main_window.py` | `test_a_voice_file_that_is_gone_is_left_out` |  |  | A voice file that is gone is left out. |
| `test_main_window.py` | `test_in_a_thread_the_buttons_wait_and_the_mix_arrives` |  |  | In a thread the buttons wait and the mix arrives. |
| `test_mix.py` | `test_without_a_voice_the_background_lasts_the_length_set` |  |  | Without a voice the background lasts the length set. |
| `test_mix.py` | `test_with_a_voice_it_is_the_lead_in_the_voice_and_the_tail` |  |  | With a voice it is the lead in the voice and the tail. |
| `test_mix.py` | `test_the_volumes_scale_each_track` |  |  | The volumes scale each track. |
| `test_mix.py` | `test_the_background_fades_in_and_out` |  |  | The background fades in and out. |
| `test_mix.py` | `test_a_mix_too_loud_is_turned_down_as_a_whole` |  |  | A mix too loud is turned down as a whole. |
| `test_mix.py` | `test_values_of_another_version_become_valid` |  |  | Values of another version become valid. |
| `test_pad.py` | `test_every_preset_has_its_sound_and_starts_from_valid_numbers` |  |  | Every preset has its sound and starts from valid numbers. |
| `test_pad.py` | `test_the_chords_notes_are_in_tune` |  |  | The chords notes are in tune. |
| `test_pad.py` | `test_a_cycle_holds_only_harmonics_below_16_khz_and_peaks_at_one` |  |  | A cycle holds only harmonics below 16 khz and peaks at one. |
| `test_pad.py` | `test_a_background_is_stereo_as_long_as_asked_and_as_loud_as_level` |  |  | A background is stereo as long as asked and as loud as level. |
| `test_pad.py` | `test_the_same_numbers_give_the_same_sound` |  |  | The same numbers give the same sound. |
| `test_pad.py` | `test_the_note_that_sounds_is_the_key` |  |  | The note that sounds is the key. |
| `test_pad.py` | `test_tone_makes_it_brighter` |  |  | Tone makes it brighter. |
| `test_pad.py` | `test_movement_makes_the_tone_drift_over_time` |  |  | Movement makes the tone drift over time. |
| `test_pad.py` | `test_space_lets_the_sound_ring_on` |  |  | Space lets the sound ring on. |
| `test_pad.py` | `test_convolving_in_blocks_is_convolving` |  |  | Convolving in blocks is convolving. |
| `test_pad.py` | `test_values_of_another_version_become_valid` |  |  | Values of another version become valid. |
| `test_player.py` | `test_without_an_output_nothing_plays_and_the_end_is_said_at_once` |  |  | Without an output nothing plays and the end is said at once. |
| `test_player.py` | `test_play_without_an_output_says_so` |  |  | Play without an output says so. |
| `test_speak_dialog.py` | `test_text_to_speech_is_found_in_the_checkout_and_missed_elsewhere` |  |  | Text to speech is found in the checkout and missed elsewhere. |
| `test_speak_dialog.py` | `test_a_text_is_spoken_saved_and_the_dialog_accepts` |  |  | A text is spoken saved and the dialog accepts. |
| `test_speak_dialog.py` | `test_a_failure_is_shown_and_make_works_again` |  |  | A failure is shown and make works again. |
| `test_speak_dialog.py` | `test_without_the_engine_the_dialog_says_where_to_set_it_up` |  |  | Without the engine the dialog says where to set it up. |
| `test_speak_dialog.py` | `test_without_text_to_speech_the_dialog_says_so` |  |  | Without text to speech the dialog says so. |

## dev/text

44 tests in 5 files.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_engine.py` | `test_a_text_is_cut_after_each_sentence` |  |  | A text is cut after each sentence. |
| `test_engine.py` | `test_an_abbreviation_an_initial_and_a_lower_case_word_end_no_sentence` |  |  | An abbreviation an initial and a lower case word end no sentence. |
| `test_engine.py` | `test_an_empty_line_is_a_paragraph_and_a_line_break_a_space` |  |  | An empty line is a paragraph and a line break a space. |
| `test_engine.py` | `test_only_the_english_female_voices_are_offered_american_first` |  |  | Only the english female voices are offered american first. |
| `test_engine.py` | `test_a_text_with_letters_of_another_script_is_not_english` |  |  | A text with letters of another script is not english. |
| `test_engine.py` | `test_the_pinned_files_are_the_half_precision_model_and_the_voices` |  |  | The pinned files are the half precision model and the voices. |
| `test_engine.py` | `test_fetch_downloads_what_is_missing_and_checks_it` |  |  | Fetch downloads what is missing and checks it. |
| `test_engine.py` | `test_fetch_keeps_no_file_that_is_not_the_pinned_one` |  |  | Fetch keeps no file that is not the pinned one. |
| `test_engine.py` | `test_a_text_is_spoken_a_sentence_at_a_time` |  |  | A text is spoken a sentence at a time. |
| `test_engine.py` | `test_the_voice_and_the_speed_have_defaults_and_limits` |  |  | The voice and the speed have defaults and limits. |
| `test_engine.py` | `test_a_cancel_ends_a_speech_at_the_next_sentence` |  |  | A cancel ends a speech at the next sentence. |
| `test_engine.py` | `test_a_new_speak_takes_the_place_of_the_one_being_made` |  |  | A new speak takes the place of the one being made. |
| `test_engine.py` | `test_what_cannot_be_spoken_is_said_and_the_loop_goes_on` |  |  | What cannot be spoken is said and the loop goes on. |
| `test_engine.py` | `test_only_english_is_spoken` |  |  | A voice of another language and a male voice, though the model has them, and a text in another script are all refused. |
| `test_engine.py` | `test_the_last_speech_is_saved_in_each_format` |  |  | The last speech is saved in each format. |
| `test_engine.py` | `test_a_long_speech_is_written_a_second_at_a_time` |  |  | A long speech is written a second at a time. |
| `test_engine.py` | `test_a_save_that_cannot_be_done_is_said` |  |  | A save that cannot be done is said. |
| `test_engine.py` | `test_the_reader_takes_commands_and_ends_with_a_quit` |  |  | The reader takes commands and ends with a quit. |
| `test_engine.py` | `test_a_save_while_a_text_is_spoken_is_refused_and_the_speech_goes_on` |  |  | A save while a text is spoken is refused and the speech goes on. |
| `test_engine_setup.py` | `test_the_engine_lives_in_the_data_folder_outside_the_checkout` |  |  | The engine lives in the data folder outside the checkout. |
| `test_engine_setup.py` | `test_installed_needs_the_python_the_packages_and_the_model_files` |  |  | Installed needs the python the packages and the model files. |
| `test_engine_setup.py` | `test_uv_makes_the_venv_with_a_python_of_its_own` |  |  | Uv makes the venv with a python of its own. |
| `test_engine_setup.py` | `test_without_uv_the_newest_fitting_python_makes_it` |  |  | Without uv the newest fitting python makes it. |
| `test_engine_setup.py` | `test_with_neither_the_message_says_what_to_install` |  |  | With neither the message says what to install. |
| `test_main_window.py` | `test_the_info_text_links_to_the_apps_place_in_the_wiki` |  |  | The info text links to the apps place in the wiki. |
| `test_main_window.py` | `test_the_icons_are_nexus_at_512_and_128_px` |  |  | The icons are nexus at 512 and 128 px. |
| `test_main_window.py` | `test_the_window_opens_on_the_engine_and_lists_its_voices` |  |  | The window opens on the engine and lists its voices. |
| `test_main_window.py` | `test_without_an_audio_output_the_window_says_so` |  |  | Without an audio output the window says so. |
| `test_main_window.py` | `test_speak_plays_the_parts_as_they_arrive` |  |  | Speak plays the parts as they arrive. |
| `test_main_window.py` | `test_nothing_is_spoken_without_a_text` |  |  | Nothing is spoken without a text. |
| `test_main_window.py` | `test_a_text_in_another_script_is_not_spoken_or_saved` |  |  | A text in another script is not spoken or saved. |
| `test_main_window.py` | `test_stop_cancels_the_speech_and_the_sound` |  |  | Stop cancels the speech and the sound. |
| `test_main_window.py` | `test_a_spoken_text_is_saved_without_making_it_again` |  |  | A spoken text is saved without making it again. |
| `test_main_window.py` | `test_an_unspoken_or_changed_text_is_made_first_without_playing` |  |  | An unspoken or changed text is made first without playing. |
| `test_main_window.py` | `test_save_as_asks_for_the_file_and_adds_the_suffix_of_the_chosen_format` |  |  | Save as asks for the file and adds the suffix of the chosen format. |
| `test_main_window.py` | `test_a_failure_is_shown_and_the_next_speak_clears_it` |  |  | A failure is shown and the next speak clears it. |
| `test_main_window.py` | `test_speak_starts_an_engine_that_stopped_and_then_speaks` |  |  | Speak starts an engine that stopped and then speaks. |
| `test_main_window.py` | `test_the_text_and_the_choices_are_remembered` |  |  | The text and the choices are remembered. |
| `test_main_window.py` | `test_without_the_engine_the_window_sets_it_up` |  |  | Without the engine the window sets it up. |
| `test_main_window.py` | `test_a_setup_step_that_fails_ends_the_setup_and_can_be_tried_again` |  |  | A setup step that fails ends the setup and can be tried again. |
| `test_player.py` | `test_without_an_output_nothing_plays_and_the_end_is_said_at_once` |  |  | Without an output nothing plays and the end is said at once. |
| `test_speech.py` | `test_the_engine_starts_speaks_saves_and_quits` |  |  | The engine starts speaks saves and quits. |
| `test_speech.py` | `test_an_engine_that_ends_by_itself_is_said` |  |  | An engine that ends by itself is said. |
| `test_speech.py` | `test_an_engine_that_cannot_start_is_said` |  |  | An engine that cannot start is said. |

## portal

217 tests in 17 files, 30.2 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_bigpicture.py` | `test_the_sound_is_there_and_the_right_length` |  |  | The sound is there and the right length. |
| `test_bigpicture.py` | `test_sounds_stay_silent_without_output_or_when_off` |  |  | Sounds stay silent without output or when off. |
| `test_bigpicture.py` | `test_stick_needs_a_real_push_and_goes_along_its_stronger_axis` |  |  | Stick needs a real push and goes along its stronger axis. |
| `test_bigpicture.py` | `test_steams_virtual_pad_only_when_steam_started_the_portal` |  |  | Steams virtual pad only when steam started the portal. |
| `test_bigpicture.py` | `test_buttons_become_actions_and_a_held_direction_repeats` |  |  | Buttons become actions and a held direction repeats. |
| `test_bigpicture.py` | `test_the_stick_moves_once_per_push_and_a_new_direction_acts_at_once` |  |  | The stick moves once per push and a new direction acts at once. |
| `test_bigpicture.py` | `test_no_pygame_means_no_controller_and_no_error` |  |  | No pygame means no controller and no error. |
| `test_bigpicture.py` | `test_nearest_tile_in_a_direction` |  |  | Nearest tile in a direction. |
| `test_bigpicture.py` | `test_view_has_a_tile_per_app_and_shows_each_state` |  | 0.2 s | View has a tile per app and shows each state. |
| `test_bigpicture.py` | `test_the_view_is_the_window_with_the_suites_name_and_a_big_icon` |  | 0.2 s | One view (owner, 01-11-2026): the window's central widget, the header with the suite's icon larger than the 96 px of an app's header, the suite's name as the title with the version and the stage. |
| `test_bigpicture.py` | `test_the_logo_plays_the_portal_tour_and_the_name_opens_the_wiki` |  | 0.2 s | Owner, 14-11-2026: the icon plays the Portal Tour in the portal (the wiki's video), the name opens the wiki; a tour that cannot be played opens the wiki's Portal Tour page in the browser. |
| `test_bigpicture.py` | `test_the_portal_opens_with_the_intro_and_its_sound` |  | 0.2 s | The intro plays before the portal shows itself (owner, 01-11-2026): dark from its first frame, the suite's name in capitals; its sound plays; when it ends the focus is on the first tile and the controller listens. |
| `test_bigpicture.py` | `test_the_intro_draws_the_suites_name_in_capitals_and_the_1024_px_icon` |  | 0.2 s | The intro draws the suites name in capitals and the 1024 px icon. |
| `test_bigpicture.py` | `test_any_key_skips_the_intro_and_stops_its_sound` |  | 0.2 s | Any key skips the intro and stops its sound. |
| `test_bigpicture.py` | `test_the_controller_skips_the_intro` |  | 0.2 s | The controller skips the intro. |
| `test_bigpicture.py` | `test_no_mode_is_kept_and_nothing_switches` |  | 0.2 s | No Suite Desktop Mode (owner, 01-11-2026): no mode pill, no F11, no setting. |
| `test_bigpicture.py` | `test_b_right_after_the_focus_came_back_is_the_press_that_closed_an_app` |  | 0.2 s | B closes an app (owner, 12-11-2026), and the portal behind it gets the focus at once and reads the same controller: that press must not close the portal too. |
| `test_bigpicture.py` | `test_escape_and_b_close_the_portal_but_skip_the_intro_first` |  | 0.3 s | Escape closes the portal (owner, 01-11-2026: "ESC does not close the board"), B too with nothing open, without a question (owner, 12-11-2026); while the intro plays, either skips it instead. |
| `test_bigpicture.py` | `test_sound_off_is_kept_and_silences_the_intro` |  | 0.3 s | Sound off is kept and silences the intro. |
| `test_bigpicture.py` | `test_without_an_audio_output_the_pill_is_disabled_with_a_reason` |  | 0.2 s | Without an audio output the pill is disabled with a reason. |
| `test_bigpicture.py` | `test_the_header_has_big_symbols_with_the_status_on_their_right` |  | 0.3 s | Big symbols in place of the pills (owner, 05-11-2026): all the same square size, their row ending at the bottom of the suite's icon; ☰ at the top right, level with the title, and the close symbol in the corner beside it (owner, 12-11-2026); on the right of the symbols the installed count over the status. |
| `test_bigpicture.py` | `test_a_symbols_badge_and_its_disabled_look` |  | 0.2 s | The badge holds a short figure; a disabled symbol draws its glyph muted, an enabled one in the theme's text. |
| `test_bigpicture.py` | `test_the_symbols_and_the_pills_work_as_before` |  | 0.2 s | The symbols and the pills work as before. |
| `test_bigpicture.py` | `test_the_focus_reaches_the_symbols_and_back_with_the_controller` |  | 0.2 s | The focus reaches the symbols and back with the controller. |
| `test_bigpicture.py` | `test_the_settings_page_holds_the_settings` |  | 0.2 s | The Settings page behind ☰ (owner, 04-11-2026, as the earlier implementation's portal): the ☰ pill or the controller's ☰ button shows it in place of the category strip and the tiles, under the same header; its pills (Desktop icons, Sound, the music and its track, the theme, the wallpaper, the clock, the weather and the touchpad, owner 05-11-2026 and 14-11-2026), each with a short line, work as before; B, Escape or ☰ again go back to the tiles. |
| `test_bigpicture.py` | `test_the_arrow_keys_move_from_a_symbol_and_enter_presses_a_button` |  | 0.2 s | The arrow keys move from a symbol and enter presses a button. |
| `test_bigpicture.py` | `test_the_local_build_banner_is_in_the_view` |  | 0.3 s | The local build banner is in the view. |
| `test_bigpicture.py` | `test_arrow_keys_move_between_tiles_and_enter_opens` |  | 0.2 s | Arrow keys move between tiles and enter opens. |
| `test_bigpicture.py` | `test_the_controller_moves_opens_and_switches_category` |  | 0.2 s | The controller moves opens and switches category. |
| `test_bigpicture.py` | `test_the_controller_is_ignored_while_the_portal_has_no_focus` |  | 0.2 s | The controller is ignored while the portal has no focus. |
| `test_bigpicture.py` | `test_a_tile_that_is_not_installed_offers_to_install_it` |  | 0.2 s | A tile that is not installed offers to install it. |
| `test_bigpicture.py` | `test_an_app_with_several_ways_to_open_offers_a_menu` |  | 0.2 s | An app with several ways to open offers a menu. |
| `test_bigpicture.py` | `test_the_tile_menu_holds_every_action` |  | 0.2 s | X or the Menu key (owner, 01-11-2026: the desktop's buttons are gone): Open, Install (Update, Reinstall) and Uninstall, grayed out where they cannot act now; Board Test has no Uninstall. |
| `test_bigpicture.py` | `test_a_right_click_or_y_updates_the_app` |  | 0.2 s | A right click on a tile, or Y on it (owner, 04-11-2026, as the earlier implementation's portal): its update, through install() and so with the board warning for an app that changes the board; no menu. |
| `test_bigpicture.py` | `test_the_controller_drives_a_menu_with_keys` |  | 0.2 s | The controller drives a menu with keys. |
| `test_bigpicture.py` | `test_an_install_stays_in_the_view` |  | 0.2 s | An install stays in the view. |
| `test_bigpicture.py` | `test_the_legend_names_the_keys` |  | 0.2 s | The legend names the keys. |
| `test_bigpicture.py` | `test_wallpaper_and_veil_reach_the_view` |  | 0.4 s | Wallpaper and veil reach the view. |
| `test_bigpicture.py` | `test_the_view_scales_down_for_a_handheld_screen` | 3 | 0.6 s | The view scales down for a handheld screen. |
| `test_bigpicture.py` | `test_each_category_keeps_its_own_columns` |  | 0.2 s | Each category keeps its own columns. |
| `test_bigpicture.py` | `test_r3_toggles_the_on_screen_keyboard_in_a_dialog_too` |  | 0.2 s | R3 (owner, 05-11-2026): Bazzite's on-screen keyboard, also while a question or the file dialog is open, where text is typed; when the desktop has none, the window says what to do. |
| `test_bigpicture.py` | `test_every_controller_action_plays_the_short_sound` |  | 0.2 s | blob.wav on every controller action (owner, 05-11-2026), not on the button that skips the intro, and not with the Sound setting off. |
| `test_bigpicture.py` | `test_keys_and_clicks_play_the_short_sound_too` |  | 0.2 s | The short sound on every action whatever it comes from (owner, 05-11-2026): a key that acts, a click on a tile or a symbol, the shortcuts, and a controller Steam turns into keys; not on a key that does nothing, a held key's repeats, a click on the room around the tiles or on text that only shows, and once for a click. |
| `test_bigpicture.py` | `test_the_key_that_skips_the_intro_is_silent` |  | 0.2 s | The key that skips the intro is silent. |
| `test_bigpicture.py` | `test_the_settings_page_scrolls_to_the_pill_with_the_focus` |  | 0.2 s | Seven settings do not fit a handheld's screen (1280 x 720): the page scrolls, and the focus takes it along. |
| `test_desktop_icons.py` | `test_add_and_remove_only_the_apps_icons` |  |  | Add and remove only the apps icons. |
| `test_desktop_icons.py` | `test_an_icon_without_a_menu_entry_is_not_the_suites` |  |  | An icon without a menu entry is not the suites. |
| `test_desktop_icons.py` | `test_no_menu_or_desktop_folder` |  |  | No menu or desktop folder. |
| `test_desktop_icons.py` | `test_every_installers_menu_entry_is_known` |  |  | A new app whose menu entry is not ps5-*.desktop needs adding to OTHERS, or its Desktop icon stays. |
| `test_keyboard.py` | `test_r3_shows_the_keyboard_for_any_input_and_hides_it_with_the_users_mode_back` |  |  | R3 shows the keyboard for any input and hides it with the users mode back. |
| `test_keyboard.py` | `test_a_keyboard_closed_some_other_way_and_the_portal_closing` |  |  | A keyboard closed some other way and the portal closing. |
| `test_keyboard.py` | `test_a_desktop_set_to_any_input_is_left_alone` |  |  | A desktop set to any input is left alone. |
| `test_keyboard.py` | `test_no_keyboard_chosen_or_no_kwin_says_what_to_do` |  |  | No keyboard chosen or no kwin says what to do. |
| `test_main_window.py` | `test_portal_shows_required_app` |  | 0.2 s | Portal shows required app. |
| `test_main_window.py` | `test_the_icon_plays_the_portal_tour_and_the_name_opens_the_wiki` |  | 0.2 s | Owner, 14-11-2026: the icon plays the Portal Tour in the portal (the wiki's video), the name opens the wiki; a tour that cannot be played opens the wiki's Portal Tour page in the browser. |
| `test_main_window.py` | `test_settings_page_and_clock_menu` |  | 0.2 s | Settings page and clock menu. |
| `test_main_window.py` | `test_clock_header_shows_date_and_time` |  | 0.2 s | Clock header shows date and time. |
| `test_main_window.py` | `test_console_release_tags_are_pruned_by_app_key` |  |  | Console release tags are pruned by app key. |
| `test_main_window.py` | `test_desktop_icon_toggle_only_manages_console_apps` |  |  | Desktop icon toggle only manages console apps. |
| `test_main_window.py` | `test_finished_install_respects_desktop_icon_setting` | 2 | 0.3 s | Finished install respects desktop icon setting. |
| `test_main_window.py` | `test_start_with_icons_off_removes_existing_console_shortcuts` |  | 0.2 s | Start with icons off removes existing console shortcuts. |
| `test_main_window.py` | `test_first_start_detects_console_shortcuts_and_toggle_restores_them` |  | 0.2 s | First start detects console shortcuts and toggle restores them. |
| `test_main_window.py` | `test_the_theme_pill_shows_the_next_theme_at_once_and_the_portal_stays_open` |  | 0.6 s | A click on the pill is the next theme, saved for every app and shown by the portal at once: the application's palette, the view's style sheets and the tiles' muted line are the new theme's. |
| `test_manifest.py` | `test_required_apps_first_board_before_the_others` |  |  | Required apps first board before the others. |
| `test_manifest.py` | `test_an_app_of_quickfixes_has_a_tile_per_quickfix` |  |  | An app of quickfixes has a tile per quickfix. |
| `test_manifest.py` | `test_rejects_a_bad_quickfix` |  |  | Rejects a bad quickfix. |
| `test_manifest.py` | `test_required_first_then_file_order` |  |  | Required first then file order. |
| `test_manifest.py` | `test_rejects` | 7 |  | Rejects. |
| `test_manifest.py` | `test_a_withdrawn_release` |  |  | A withdrawn release. |
| `test_manifest.py` | `test_board_change_text` |  |  | What an app changes on the board, for its tooltip and the box at the top of its wiki chapter: one line of plain sentences, however the manifest wraps it; "" in a manifest from before it. |
| `test_manifest.py` | `test_a_category_for_its_tab` |  |  | A category for its tab. |
| `test_manifest.py` | `test_no_development_tab_and_no_earlier_categories` |  |  | The four categories, no Development tab and no categories of earlier releases; [checkout.*] tables are not read. |
| `test_manifest.py` | `test_shipped_manifest_has_a_category_for_every_app` |  |  | Shipped manifest has a category for every app. |
| `test_manifest.py` | `test_short_name_for_the_tile` |  |  | Short name for the tile. |
| `test_manifest.py` | `test_bad_sha_and_toml` |  |  | Bad sha and toml. |
| `test_manifest.py` | `test_shipped_manifest_lists_every_app_with_bazzite_test_first` |  |  | Shipped manifest lists every app with bazzite test first. |
| `test_manifest.py` | `test_shipped_manifest_install_scripts_exist` |  |  | Shipped manifest install scripts exist. |
| `test_manifest.py` | `test_board_changing_apps_are_marked` |  |  | Board changing apps are marked. |
| `test_music.py` | `test_the_portal_ships_its_own_track` |  |  | The portal ships its own track. |
| `test_music.py` | `test_a_track_of_your_own_is_a_copy_in_the_state_folder` |  |  | The user's track is copied into the portal's state folder, in place of the one before; without one the portal plays its own. |
| `test_music.py` | `test_the_player_stays_silent_without_a_track` |  |  | The real player: no track, or one that is gone, makes no player and no error; pause and stop before play too. |
| `test_music.py` | `test_the_music_plays_while_the_portal_is_in_front` |  | 0.2 s | The music starts once the intro is over, waits while another window has the focus (a game, an app), and plays on when the portal is back. |
| `test_music.py` | `test_the_music_pill_is_apart_from_the_sound_pill` |  | 0.4 s | Music has a switch of its own (owner, 14-11-2026): off, the music stops and Sound stays as it is, and the other way round; the choice is kept. |
| `test_music.py` | `test_no_music_without_an_audio_output` |  | 0.2 s | No music without an audio output. |
| `test_music.py` | `test_the_music_waits_for_the_portal_tour` |  | 0.2 s | The music waits for the portal tour. |
| `test_music.py` | `test_the_music_track_pill` |  | 0.2 s | The Music track pill: Built-in until the user chooses a track of their own (Custom), which plays at once; The portal's track brings the portal's own back. |
| `test_portal_update.py` | `test_compare_names_the_changed_apps` |  |  | Compare names the changed apps. |
| `test_portal_update.py` | `test_compare_names_a_withdrawn_app` |  |  | Compare names a withdrawn app. |
| `test_portal_update.py` | `test_summary_and_details` |  |  | Summary and details. |
| `test_portal_update.py` | `test_check_reads_the_pins_at_the_release_tag` |  |  | Check reads the pins at the release tag. |
| `test_portal_update.py` | `test_check_without_details_or_release` |  |  | Check without details or release. |
| `test_portal_update.py` | `test_check_reads_the_tarballs_sha256_and_the_running_build` |  |  | The newest release's SHA256SUMS tells a new build of this version (owner, 03-11-2026); build.sha256 beside the program is what this portal came from. |
| `test_shortcuts.py` | `test_steam_and_the_file_manager` |  |  | Steam and the file manager. |
| `test_shortcuts.py` | `test_youtube_needs_brave_browsers_flatpak` |  |  | Youtube needs brave browsers flatpak. |
| `test_shortcuts.py` | `test_github_opens_in_the_desktops_own_browser` |  |  | github.com with xdg-open; the browser's window is the one KWin brings to the front, when it can be asked. |
| `test_shortcuts.py` | `test_the_settings_of_the_desktop_that_is_there` | 4 |  | KDE Plasma's System Settings, else the module alone, else GNOME's Settings (not only the owner's desktop). |
| `test_sources.py` | `test_expected_sha256` |  |  | Expected sha256. |
| `test_sources.py` | `test_release_download_verified_with_sha256sums` |  |  | Release download verified with sha256sums. |
| `test_sources.py` | `test_pinned_sha256_wins_and_mismatch_refuses` |  |  | Pinned sha256 wins and mismatch refuses. |
| `test_sources.py` | `test_the_portal_update_keeps_its_tarball_beside_the_folder` |  |  | The portal's own update (owner, 04-11-2026): checked against SHA256SUMS (or the sha256 given), unpacked into <work>/<tag> with <tag>.tar.gz beside it, so install.sh records the build; the folder is emptied first. |
| `test_sources.py` | `test_download_errors` |  |  | Download errors. |
| `test_sources.py` | `test_wrong_top_folder` |  |  | Wrong top folder. |
| `test_sources.py` | `test_safe_extract_refuses_escapes` | 2 |  | Safe extract refuses escapes. |
| `test_sources.py` | `test_safe_extract_refuses_links_out` |  |  | Safe extract refuses links out. |
| `test_sources.py` | `test_checkout_stages_app_with_core` |  |  | Checkout stages app with core. |
| `test_sources.py` | `test_prune_keeps_only_the_installed_release` |  |  | Prune keeps only the installed release. |
| `test_sources.py` | `test_suite_checkout` |  |  | Suite checkout. |
| `test_sources.py` | `test_is_installed` |  |  | Is installed. |
| `test_sources.py` | `test_records_round_trip` |  |  | Records round trip. |
| `test_sources.py` | `test_records_follow_an_app_renamed_in_the_suite` |  |  | A copy installed under an app's old key (btpair) is recorded under its new key (bluetooth) with its tag's prefix renamed, so the portal neither asks for a reinstall nor offers the version it has as an update. |
| `test_sources.py` | `test_the_record_of_a_checkout_install` |  |  | The record of a checkout install. |
| `test_state_dir.py` | `test_the_state_folder_is_not_the_installed_portals_folder` |  |  | The state folder is not the installed portals folder. |
| `test_state_dir.py` | `test_the_installed_copy_is_the_portal_folder_in_the_suites_folder` |  |  | install.sh's copy, ~/.local/share/<suite>/portal: the portal compares its build and offers a restart there; a checkout's portal/ is no installed copy. |
| `test_status.py` | `test_the_clock_reads_as_the_owner_wrote_it` |  |  | The clock reads as the owner wrote it. |
| `test_status.py` | `test_the_line_has_the_load_from_the_second_sample` |  |  | The line has the load from the second sample. |
| `test_status.py` | `test_the_gpu_load_from_the_engine_time_without_a_load_sensor` |  |  | A stock Cyan Skillfish kernel has no gpu_busy_percent: the engine time of this user's GPU clients counts. |
| `test_status.py` | `test_the_patched_gpu_metrics_count_only_when_mounted` |  |  | The patched gpu metrics count only when mounted. |
| `test_status.py` | `test_what_the_system_does_not_report_is_left_out` |  |  | What the system does not report is left out. |
| `test_status.py` | `test_the_clock_as_the_settings_set_it` |  |  | The Settings page's clock (owner, 05-11-2026): 12 or 24 hours, the seconds, the board's zone, CET or UTC. |
| `test_status.py` | `test_the_loads_without_the_clock` |  |  | The window samples the loads every 2 s and draws the clock every second: loads() is the line's first part. |
| `test_sysinfo.py` | `test_the_owners_board` |  |  | The owners board. |
| `test_sysinfo.py` | `test_two_gpus_a_sata_drive_and_a_usb_stick` |  |  | Two gpus a sata drive and a usb stick. |
| `test_sysinfo.py` | `test_a_system_that_reports_nothing` |  |  | No sysfs, /proc or /etc (another OS, a container): only what Python itself knows. |
| `test_sysinfo.py` | `test_as_text` |  |  | As text. |
| `test_touchpad_and_raise.py` | `test_a_finger_moves_the_pointer_and_a_press_clicks` |  |  | A finger moves the pointer and a press clicks. |
| `test_touchpad_and_raise.py` | `test_the_virtual_mouse_sends_whole_pixels_and_fails_quietly` |  |  | The virtual mouse sends whole pixels and fails quietly. |
| `test_touchpad_and_raise.py` | `test_kwin_is_asked_to_bring_the_apps_window_forward` |  |  | Kwin is asked to bring the apps window forward. |
| `test_touchpad_and_raise.py` | `test_without_kwin_nothing_happens` |  |  | Without kwin nothing happens. |
| `test_touchpad_and_raise.py` | `test_pygame_ces_touch_events_are_read_with_their_finger_id` |  |  | pygame-ce names the finger finger_id (a DualShock 4 on the owner's board, 05-11-2026: 'finger' crashed the reader at the first touch); the touchpad's press is SDL's button 20. |
| `test_tour.py` | `test_a_tour_that_cannot_be_played_says_so_once_and_closes` |  |  | A tour that cannot be played says so once and closes. |
| `test_tour.py` | `test_space_pauses_and_plays_on_and_does_not_close` |  |  | Space pauses and plays on and does not close. |
| `test_wallpaper.py` | `test_the_example_is_shipped_and_meets_the_rules` |  |  | The example is shipped and meets the rules. |
| `test_wallpaper.py` | `test_the_portal_starts_with_the_example` |  |  | The portal starts with the example. |
| `test_wallpaper.py` | `test_no_wallpaper_is_remembered_until_the_example_is_chosen_again` |  |  | No wallpaper is remembered until the example is chosen again. |
| `test_wallpaper.py` | `test_a_picture_of_the_users_own_goes_before_the_example_and_ends_no_wallpaper` |  |  | A picture of the users own goes before the example and ends no wallpaper. |
| `test_weather.py` | `test_a_search_lists_the_places_and_skips_a_broken_one` |  |  | A search lists the places and skips a broken one. |
| `test_weather.py` | `test_the_current_weather_and_its_symbol` |  |  | The current weather and its symbol. |
| `test_weather.py` | `test_a_place_is_kept_as_json` |  |  | A place is kept as json. |
| `test_weather.py` | `test_open_meteo_down_or_unreachable_says_so` |  |  | Open meteo down or unreachable says so. |
| `test_window.py` | `test_bazzite_test_first_without_uninstall` |  | 0.2 s | Bazzite test first without uninstall. |
| `test_window.py` | `test_every_app_has_its_icon` |  | 0.2 s | Every app has its icon. |
| `test_window.py` | `test_the_quickfixes_are_tiles_of_their_own` |  |  | PS5 Quickfix: a tile per quickfix in Utilities, none of its own (owner, 15-11-2026); each opens its quickfix, and the board warning names the quickfix that changes the board. |
| `test_window.py` | `test_a_quickfixes_tile_installs_its_app` |  |  | Reinstall on a quickfix's tile reinstalls PS5 Quickfix: one install, recorded under the app's key. |
| `test_window.py` | `test_open_menu_shows_each_window_icon` |  | 0.2 s | Open menu shows each window icon. |
| `test_window.py` | `test_an_app_without_an_icon_file_still_has_a_tile` |  | 0.2 s | An app without an icon file still has a tile. |
| `test_window.py` | `test_short_names_drop_the_suite_prefix` |  | 0.2 s | Short names drop the suite prefix. |
| `test_window.py` | `test_a_short_name_from_apps_toml_is_the_tiles` |  | 0.2 s | A short name from apps toml is the tiles. |
| `test_window.py` | `test_a_tile_opens_only_an_installed_program` |  | 0.2 s | A tile opens only an installed program. |
| `test_window.py` | `test_icon_is_greyed_until_installed` |  | 0.2 s | Icon is greyed until installed. |
| `test_window.py` | `test_board_warning_under_the_icon` |  | 0.2 s | Board warning under the icon. |
| `test_window.py` | `test_states_follow_detection_and_records` |  | 0.2 s | States follow detection and records. |
| `test_window.py` | `test_bazzite_test_has_only_reinstall` |  | 0.2 s | With the arrow into a tray, as every app (owner, 14-10-2026), and the version it reinstalls. |
| `test_window.py` | `test_board_change_needs_confirmation` |  | 0.2 s | Board change needs confirmation. |
| `test_window.py` | `test_no_warning_for_board_test` |  | 0.2 s | No warning for board test. |
| `test_window.py` | `test_install_success_records_tag` |  | 0.2 s | Install success records tag. |
| `test_window.py` | `test_failed_install_warns_and_records_nothing` |  | 0.2 s | Failed install warns and records nothing. |
| `test_window.py` | `test_uninstall_forgets_release` |  | 0.2 s | Uninstall forgets release. |
| `test_window.py` | `test_closed_terminal_can_be_abandoned` |  | 0.2 s | Closed terminal can be abandoned. |
| `test_window.py` | `test_shell_line_quotes_folder` |  |  | Shell line quotes folder. |
| `test_window.py` | `test_red_dot_and_count_for_updates` |  | 0.2 s | Red dot and count for updates. |
| `test_window.py` | `test_the_installed_line_counts_installed_of_listed` |  | 0.2 s | Installed apps: installed / listed, a withdrawn app not counted (owner, 21-10-2026). |
| `test_window.py` | `test_install_all_updates_one_after_the_other` |  | 0.3 s | Install all updates: one question for every app the notice names (owner, 21-10-2026), with the board warning when one changes the board; then each in its own terminal, the next only when the one before ended (an installer waiting for the sudo password holds the batch); one message at the end names those that failed. |
| `test_window.py` | `test_stop_waiting_ends_the_batch` |  | 0.2 s | Stop waiting ends the batch. |
| `test_window.py` | `test_install_all_apps_is_a_symbol_that_fills_the_open_category` |  | 0.2 s | Install all apps (owner, 26-10-2026; in the header since the tabs went, 01-11-2026, a big symbol since 05-11-2026, the number of apps of the open category not installed yet in its tooltip). |
| `test_window.py` | `test_no_updates_no_batch` |  | 0.2 s | No updates no batch. |
| `test_window.py` | `test_updates_outside_the_suite` |  | 0.2 s | In orange beside the category strip, and on the app's tile (owner, 01-11-2026: the notice is a menu). |
| `test_window.py` | `test_circular_arrow_and_count_for_reinstalls` |  | 0.2 s | Circular arrow and count for reinstalls. |
| `test_window.py` | `test_not_installed_and_withdrawn_need_no_reinstall` |  | 0.2 s | Not installed and withdrawn need no reinstall. |
| `test_window.py` | `test_local_build_banner` |  | 0.3 s | Local build banner. |
| `test_window.py` | `test_newer_portal_release_is_offered` |  | 0.2 s | The orange banner beside the category strip (owner, 04-11-2026, as the earlier implementation's portal); a click on it updates the portal, as Y does. |
| `test_window.py` | `test_a_new_build_of_this_version_is_offered` |  | 1.1 s | A release built again under the portal's own version (owner, 03-11-2026): offered when its tarball's sha256 differs from the build this portal came from; not from a checkout, not for the same build. |
| `test_window.py` | `test_a_download_counts_its_megabytes` |  | 0.2 s | The tile says how far a download is (owner, 03-11-2026: Downloading… for a 90 MB release looked like a hang): the part file's size, read every PROGRESS_MS while the job runs. |
| `test_window.py` | `test_the_exit_asks_nothing` |  | 0.2 s | Escape (B) and the close symbol close the portal without a question (owner, 12-11-2026). |
| `test_window.py` | `test_the_desktops_close_asks_only_while_something_runs` |  | 0.2 s | The desktops close asks only while something runs. |
| `test_window.py` | `test_a_shortcut_starts_its_program` |  | 0.2 s | The header's shortcuts (owner, 12-11-2026): the file manager, Steam, YouTube in Brave Browser, GitHub, and the desktop's Bluetooth, network, sound and display settings. |
| `test_window.py` | `test_a_key_for_each_controller_action` |  | 0.2 s | Steam's desktop layout turns a pad's buttons into keys (owner, 05-11-2026): U, S, K and M do what Y, ☰, R3 and X do, for the buttons it gives no key of their own. |
| `test_window.py` | `test_the_s_key_opens_the_settings` |  | 0.2 s | The s key opens the settings. |
| `test_window.py` | `test_the_arrow_keys_move_between_a_questions_buttons` |  | 0.2 s | With Steam's desktop layout a controller is the arrow keys and Enter: Qt's questions take them as they are. |
| `test_window.py` | `test_no_portal_offer_when_not_newer_or_offline` | 3 | 0.6 s | No portal offer when not newer or offline. |
| `test_window.py` | `test_tiles_flow_in_file_order` |  | 0.3 s | Tiles flow in file order. |
| `test_window.py` | `test_a_category_per_tab_in_order` |  | 0.2 s | A category per tab in order. |
| `test_window.py` | `test_bazzite_test_is_the_first_tile_on_sustainable` |  | 0.2 s | Board Test is pinned as the first tile on Sustainable (owner, 20-10-2026). |
| `test_window.py` | `test_the_portal_always_opens_on_the_first_category` |  | 0.3 s | Whatever category was open last (owner, 20-10-2026). |
| `test_window.py` | `test_a_line_of_the_notice_goes_to_the_tile_of_its_app` |  | 0.2 s | A line of the notice goes to the tile of its app. |
| `test_window.py` | `test_the_tools_of_the_development_tab_are_utilities` |  | 0.2 s | No Development tab (owner, 27-10-2026). |
| `test_window.py` | `test_no_category_without_its_apps` |  | 0.2 s | No category without its apps. |
| `test_window.py` | `test_portal_offer_names_the_app_updates` |  | 0.4 s | Portal offer names the app updates. |
| `test_window.py` | `test_y_downloads_checks_and_installs_the_portal_then_restarts` |  | 0.2 s | Y (or a right click, or the banner) while a newer portal is out (owner, 04-11-2026, as the earlier implementation's portal): its tarball downloaded and checked, unpacked with the tarball beside it (install.sh records the build), its install.sh run in a terminal, and the new portal started when that ended well. |
| `test_window.py` | `test_a_portal_update_that_fails_says_so` |  | 0.2 s | A portal update that fails says so. |
| `test_window.py` | `test_first_start_asks_about_app_icons` |  | 0.2 s | First start asks about app icons. |
| `test_window.py` | `test_keeping_the_icons` |  | 0.2 s | Keeping the icons. |
| `test_window.py` | `test_no_question_without_app_icons` |  | 0.2 s | No question without app icons. |
| `test_window.py` | `test_an_install_with_icons_off_removes_the_new_icon` |  | 0.2 s | An install with icons off removes the new icon. |
| `test_window.py` | `test_a_withdrawn_app_is_not_available` |  | 0.2 s | A withdrawn app is not available. |
| `test_window.py` | `test_the_portal_removes_a_withdrawn_app` |  | 0.2 s | The portal removes a withdrawn app. |
| `test_window.py` | `test_a_withdrawn_app_that_could_not_be_removed_stays_removable` |  | 0.2 s | A withdrawn app that could not be removed stays removable. |
| `test_window.py` | `test_restart_into_a_portal_installed_meanwhile` |  | 0.2 s | Restart into a portal installed meanwhile. |
| `test_window.py` | `test_restart_leaves_a_folder_that_is_gone` |  | 0.2 s | The portal's update replaces the folder the portal runs in: the restart's shell starts in one that exists. |
| `test_window.py` | `test_restart_that_cannot_start` |  | 0.2 s | Restart that cannot start. |
| `test_window.py` | `test_no_restart_from_a_checkout` |  | 0.2 s | No restart from a checkout. |
| `test_window.py` | `test_one_theme_for_every_app` |  | 0.7 s | The theme pill shows the chosen theme; a click takes the next one, for every app; its tooltip says when it shows. |
| `test_window.py` | `test_the_header_is_an_apps_header_with_symbols` |  | 0.2 s | The suite's icon, spanning the name, ☰ and the close symbol at the top right and the row of big symbols (owner, 05-11-2026, in place of the pills): Refresh, Sys info, Install all apps and Install all updates, then the shortcuts (owner, 12-11-2026): Files, Steam, YouTube, GitHub, Bluetooth, Network, Volume and Screen, what each does in its tooltip; on their right the installed count over the status. |
| `test_window.py` | `test_the_sys_info_symbol_opens_one_window_read_each_time` |  | 0.2 s | Sys info (owner, 20-10-2026): a small window with what the system reports, read again each time it opens; Copy puts it on the clipboard as text. |
| `test_window.py` | `test_the_wallpaper` |  | 0.4 s | A picture of at least 1920 x 1080 in 16:9 becomes the wallpaper (a copy in the portal's state folder); another is refused, with the rules (owner, 20-10-2026). |
| `test_window.py` | `test_the_example_wallpaper` |  | 0.5 s | The portal ships an example wallpaper (owner, 20-10-2026) and starts with it (owner, 15-11-2026): it is the wallpaper until the user chooses a picture of their own or none, and No wallpaper is remembered. |
| `test_window.py` | `test_the_wallpapers_used_before` |  | 0.8 s | The portal remembers where the last 10 wallpapers came from, newest first and each once, and offers them again in the Wallpaper pill's menu (owner, 20-10-2026): the current one ticked, one moved or deleted grayed out. |
| `test_window.py` | `test_the_wallpapers_transparency` |  | 0.4 s | A slider in the Wallpaper pill's menu sets how much of the theme's color lies over the picture, while it moves and for the next start (owner, 20-10-2026): 60 % at first, as before, up to 90 %; off without a wallpaper. |
| `test_window.py` | `test_a_checkout_install_is_compared_by_its_version` |  | 0.2 s | A portal from a release, an app installed from a checkout (owner, 26-10-2026): the recorded version against the pin, as a tag's; a record without one (portal 9.2.0 and earlier) needs a reinstall. |
| `test_window.py` | `test_a_checkout_portal_shows_its_own_installs_as_installed` |  | 0.2 s | A checkout portal shows its own installs as installed. |
| `test_window.py` | `test_a_checkout_install_records_the_staged_version` |  | 0.2 s | A checkout install records the staged version. |
| `test_window.py` | `test_a_running_app_comes_to_the_front_without_a_second_warning` |  | 0.2 s | Pressing the tile of an app that runs (behind the portal) starts it again, which asks it to show itself, and has KWin make its window the active one: by its app id, the launcher's name, and the process the portal started. |
| `test_window.py` | `test_the_clock_pill_sets_the_hours_the_seconds_and_the_zone` |  | 0.2 s | The clock pill sets the hours the seconds and the zone. |
| `test_window.py` | `test_the_status_is_three_lines` |  |  | A line each (owner, 12-11-2026), whatever the room: the loads, the date and time, and the weather with a place chosen (its symbol, the place, the temperature and the sky); two lines without a place. |
| `test_window.py` | `test_the_weather_shows_under_the_clock_once_a_place_is_chosen` |  | 0.2 s | No place: no weather, nothing asked. |
| `test_window.py` | `test_a_long_place_name_ends_in_an_ellipsis_on_its_pill` |  | 0.3 s | A long place name ends in an ellipsis on its pill. |
| `test_window.py` | `test_the_touchpad_moves_the_pointer_only_while_the_portal_has_the_focus` |  | 0.2 s | The touchpad moves the pointer only while the portal has the focus. |
| `test_window.py` | `test_the_touchpad_pill_steps_through_the_speeds` |  | 0.2 s | The Touchpad pill (owner, 05-11-2026): a click for the next speed, at once and kept, round to the slowest. |

## tools

216 tests in 37 files, 10.2 s in a local run.

| File | Test | Cases | Time | What it checks |
|---|---|---|---|---|
| `test_all_tests.py` | `test_the_list_is_written_from_the_tests` |  |  | The list is written from the tests. |
| `test_all_tests.py` | `test_the_cases_and_times_of_a_run_stay_until_the_next_one` |  |  | Written again without a run, the file keeps what a run gave it: only the tests themselves change it. |
| `test_all_tests.py` | `test_the_suites_list_is_its_tests` |  |  | ALL-TESTS.md is what tools/all_tests.py writes from the tests now: run it after a test is added, renamed or removed (Nexus Release Tool's Commit does). |
| `test_all_tests.py` | `test_the_wiki_shows_it_under_development` |  |  | The wiki shows it under development. |
| `test_apply_design.py` | `test_the_mock_is_written_into_the_stylesheet_and_emptied` |  |  | The mock is written into the stylesheet and emptied. |
| `test_apply_design.py` | `test_an_empty_or_missing_mock_changes_nothing` |  |  | An empty or missing mock changes nothing. |
| `test_apply_design.py` | `test_main_names_the_files_it_wrote` |  |  | Main names the files it wrote. |
| `test_build_release.py` | `test_bazzite_test_layout` |  | 0.1 s | Bazzite test layout. |
| `test_build_release.py` | `test_modes_and_owner` |  |  | Modes and owner. |
| `test_build_release.py` | `test_sums_and_notes` |  |  | Sums and notes. |
| `test_build_release.py` | `test_reproducible` |  | 0.1 s | Reproducible. |
| `test_build_release.py` | `test_version_must_match` |  |  | Version must match. |
| `test_build_release.py` | `test_an_apps_release_has_the_standard_layout_and_omits_suite_marker` |  | 0.2 s | Bazzite DatStation: an app with no .standalone. |
| `test_build_release.py` | `test_native_wheel_is_required_and_named` |  | 0.1 s | Native wheel is required and named. |
| `test_build_release.py` | `test_the_native_wheel_from_a_folder_outside_the_checkout` |  | 0.1 s | release.yml builds the wheel outside the checkout and names the folder in PS5_NATIVE_WHEEL_DIR: the wheel is taken from there and lands in the app's own wheel folder in the tarball. |
| `test_build_release.py` | `test_checkout_only_app_has_no_release` |  |  | An app with .checkout-only (Nexus Release Tool, Installer Tests) is never built: the marker is refused. |
| `test_build_release.py` | `test_portal_needs_and_verifies_bundle` |  | 0.4 s | Portal needs and verifies bundle. |
| `test_build_release.py` | `test_only_a_portal_release_says_the_stage` |  |  | Only a portal release says the stage. |
| `test_build_release.py` | `test_wrong_pin_refused` |  |  | Wrong pin refused. |
| `test_build_release.py` | `test_tampered_bundle_refused` |  |  | Tampered bundle refused. |
| `test_build_release.py` | `test_the_bundle_as_release_yml_downloads_it` |  | 0.3 s | release.yml downloads each required release into a folder named after its tag, its SHA256SUMS beside it: with no checksum pinned yet (a release about to be made), each is checked against its own SHA256SUMS. |
| `test_build_release.py` | `test_latest_changes` |  |  | Latest changes. |
| `test_check_manifest.py` | `test_bump_level` | 6 |  | Bump level. |
| `test_check_manifest.py` | `test_unchanged_needs_nothing` |  |  | Unchanged needs nothing. |
| `test_check_manifest.py` | `test_portal_bump_at_least_app_bump` | 6 |  | Portal bump at least app bump. |
| `test_check_manifest.py` | `test_largest_app_bump_counts` |  |  | Largest app bump counts. |
| `test_check_manifest.py` | `test_other_changes_need_a_patch_bump` |  |  | Other changes need a patch bump. |
| `test_check_manifest.py` | `test_added_app_needs_minor` |  |  | Added app needs minor. |
| `test_check_manifest.py` | `test_withdrawn_app_needs_minor` |  |  | Withdrawn app needs minor. |
| `test_check_manifest.py` | `test_app_moving_back_is_refused` |  |  | App moving back is refused. |
| `test_check_manifest.py` | `test_latest_portal_tag` |  |  | Latest portal tag. |
| `test_check_manifest.py` | `test_bump_is_counted_since_the_last_portal_release` |  |  | The owner's case of 17-10-2026: the push with the apps' releases carried the portal bump (1.12.0 -> 1.13.0), and the next push, with their checksums pinned, was asked for 1.13.1 against the last push. |
| `test_check_manifest.py` | `test_shipped_manifest_passes_without_required_tags` |  |  | Shipped manifest passes without required tags. |
| `test_check_manifest.py` | `test_wiki_board_box` |  |  | The box right after the chapter's title, its lines joined; none when the chapter opens with anything else. |
| `test_check_manifest.py` | `test_every_board_changing_app_says_what_it_changes` |  |  | An app marked changes_board has a board_change, and its wiki chapter opens with the same text in the box; an app not so marked has none (owner, 03-11-2026). |
| `test_check_manifest.py` | `test_shipped_manifest_and_wiki_say_what_each_app_changes` |  |  | Shipped manifest and wiki say what each app changes. |
| `test_check_manifest.py` | `test_every_app_needs_a_category` |  | 0.1 s | Every app needs a category. |
| `test_check_manifest.py` | `test_no_checkout_tables` |  |  | The portal lists only released apps (owner, 27-10-2026): the tools that run from the checkout are started there, not from a Development tab. |
| `test_check_manifest.py` | `test_checkout_table_change_needs_a_patch_bump` |  |  | Checkout table change needs a patch bump. |
| `test_check_release.py` | `test_draft_uses_homebrews_gh` |  |  | Draft uses homebrews gh. |
| `test_check_upstream.py` | `test_the_shadps4_pin_is_read_from_emulator_py` |  |  | The shadps4 pin is read from emulator py. |
| `test_check_upstream.py` | `test_shadps4_in_step` |  |  | Shadps4 in step. |
| `test_check_upstream.py` | `test_a_newer_shadps4_gives_what_the_pin_needs` | 3 |  | A newer shadps4 gives what the pin needs. |
| `test_check_upstream.py` | `test_exit_codes` |  |  | Exit codes. |
| `test_check_upstream.py` | `test_an_older_shadps4_is_not_newer` |  |  | An older shadps4 is not newer. |
| `test_check_upstream.py` | `test_a_replaced_shadps4_zip` |  |  | A replaced shadps4 zip. |
| `test_check_upstream.py` | `test_the_helixsr_constants_are_read_from_acquire_py` |  |  | The helixsr constants are read from acquire py. |
| `test_check_upstream.py` | `test_helixsr_in_step` |  |  | Helixsr in step. |
| `test_check_upstream.py` | `test_a_newer_helixsr` |  |  | A newer helixsr. |
| `test_check_upstream.py` | `test_a_new_helixsr_major_is_not_offered` |  |  | A new helixsr major is not offered. |
| `test_check_upstream.py` | `test_the_fallback_the_notes_name` | 4 |  | The fallback the notes name. |
| `test_check_upstream.py` | `test_a_fallback_without_its_zip` |  |  | A fallback without its zip. |
| `test_check_upstream.py` | `test_the_pins_are_read_from_the_apps` | 3 |  | The pins are read from the apps. |
| `test_check_upstream.py` | `test_a_newer_release_moves_a_pin` | 3 |  | A newer release moves a pin. |
| `test_check_upstream.py` | `test_the_report_for_the_issue` |  |  | The report for the issue. |
| `test_check_upstream.py` | `test_the_builds_are_read_from_the_apps` | 2 |  | The builds are read from the apps. |
| `test_check_upstream.py` | `test_vita3k_a_higher_build_number_is_newer` |  |  | Vita3k a higher build number is newer. |
| `test_check_upstream.py` | `test_xenia_a_build_published_later_is_newer` |  |  | Xenia a build published later is newer. |
| `test_check_upstream.py` | `test_the_pinned_appimage` | 2 |  | The pinned appimage. |
| `test_check_upstream.py` | `test_the_new_pins_are_read_from_the_apps` |  |  | The new pins are read from the apps. |
| `test_check_upstream.py` | `test_ffmpeg_and_libva` |  |  | A point release on the pinned branch, a newer branch and a newer libva are each a line; a development tag (n8.1-dev) is no release. |
| `test_check_upstream.py` | `test_webcam_firmware` |  |  | The file at the pinned commit, and the same file on the default branch: changed or gone there is a line. |
| `test_check_upstream.py` | `test_speedtest` |  |  | Speedtest. |
| `test_check_versions.py` | `test_cargo_lock_entry_of_the_crate_itself` |  |  | Cargo lock entry of the crate itself. |
| `test_check_versions.py` | `test_copies_with_a_comment_are_read_and_odd_ones_reported` |  |  | Copies with a comment are read and odd ones reported. |
| `test_check_versions.py` | `test_the_suite_passes` |  | 0.3 s | The suite passes. |
| `test_check_versions.py` | `test_core_the_portal_and_the_apps_not_dev` |  | 0.2 s | The released folders have a VERSION; the development apps in dev/ have none and are not checked. |
| `test_check_versions.py` | `test_venvs_caches_and_tests_hold_no_copies` |  |  | Venvs caches and tests hold no copies. |
| `test_ci_local.py` | `test_every_job_of_ci_yml_and_every_matrix_entry` |  | 0.1 s | Every job of ci yml and every matrix entry. |
| `test_ci_local.py` | `test_a_matrix_from_a_plan_job_is_read_by_running_it` |  |  | ci.yml's pytest matrix is the plan job's output (tools/ci_matrix.py, fromJSON): the plan job's steps run here and their $GITHUB_OUTPUT lines give the entries; the plan job itself is a job too. |
| `test_ci_local.py` | `test_a_job_the_plan_leaves_out_is_not_run_and_its_outputs_reach_the_steps` |  |  | ci.yml's plan job names what a push runs (tools/ci_matrix.py plan): a job whose if compares one of its outputs is skipped when it is false, as on GitHub, and a step reads an output as its text. |
| `test_ci_local.py` | `test_expressions_and_selection` |  | 0.1 s | Expressions and selection. |
| `test_ci_local.py` | `test_requirement_files_follow_includes` |  |  | Requirement files follow includes. |
| `test_ci_local.py` | `test_ci_runs_for_every_branch_push_and_no_tag` |  |  | A push to a branch runs CI, a tag does not (tag-release.sh tags only a commit CI passed). |
| `test_ci_local.py` | `test_only_the_workflows_a_push_starts` |  |  | Without job names, the workflows GitHub starts for the push: ci.yml has no paths filter, so every push. |
| `test_ci_matrix.py` | `test_the_pytest_matrix_is_every_folder_with_tests` |  |  | The pytest matrix is every folder with tests. |
| `test_ci_matrix.py` | `test_the_suite_matches_its_workflow_and_the_layout_rule` |  | 0.1 s | ci.yml reads its matrix from this tool, and the list is what tools/tests/test_layout.py wants: every folder with tests/, core, tools and dev/ among them. |
| `test_ci_matrix.py` | `test_the_command_line` |  | 0.1 s | The command line. |
| `test_ci_matrix.py` | `test_a_push_runs_the_jobs_of_what_it_changed` |  |  | One app: its tests and tools' (the repository's rules), and the installer tests that name it. |
| `test_ci_matrix.py` | `test_a_shared_file_is_the_change_of_every_folder_whose_tests_read_it` |  |  | The release commit pins apps.toml: the portal's tests, and those of the folders that read the manifest. |
| `test_ci_matrix.py` | `test_everything_when_the_change_is_not_known_or_every_job_stands_on_it` |  |  | Everything when the change is not known or every job stands on it. |
| `test_ci_matrix.py` | `test_the_plan_on_the_command_line` |  | 0.1 s | The plan on the command line. |
| `test_ci_state.py` | `test_state_of_the_runs` |  |  | State of the runs. |
| `test_ci_state.py` | `test_waits_while_ci_runs_then_answers` |  |  | Waits while ci runs then answers. |
| `test_ci_state.py` | `test_gives_up_after_the_wait_and_reports_failure_at_once` |  |  | Gives up after the wait and reports failure at once. |
| `test_ci_state.py` | `test_a_commit_without_a_run_is_answered_within_minutes` |  |  | A suite's CI runs only when a push changes its paths (29-10-2026): a commit that has no run after the grace gets "none" then, with the reason, not after the whole wait; a run that appears in time is waited for. |
| `test_ci_state.py` | `test_unreachable_and_the_stub` |  |  | Unreachable and the stub. |
| `test_ci_state.py` | `test_a_suite_of_its_own_asks_for_its_own_workflow` |  |  | ci.yml by default (Nexus and the Bazzite Console Suite); --workflow another suite's CI (owner, 27-10-2026: one suite's CI never holds another suite's releases). |
| `test_ci_state.py` | `test_a_release_commit_is_answered_by_its_work_commit` |  |  | --release-commit (owner, 30-10-2026): a commit that only writes a release takes the CI of its parent, the work commit; one that changes more, or whose work commit has no run of the workflow, takes its own. |
| `test_design_panel.py` | `test_only_while_serving` |  |  | Only while serving. |
| `test_design_panel.py` | `test_the_panel_names_the_files_of_each_wiki` |  |  | Copy CSS goes to the wiki's own stylesheet: the panel says which, as a path in the checkout. |
| `test_design_panel.py` | `test_the_address_is_relative_to_the_page` |  |  | The address is relative to the page. |
| `test_design_panel.py` | `test_the_mock_is_stored_and_returned` |  |  | The mock is stored and returned. |
| `test_design_panel.py` | `test_a_bad_post_changes_nothing` |  |  | A bad post changes nothing. |
| `test_design_panel.py` | `test_screens_shows_pc_laptop_and_handheld_sizes` |  |  | Screens shows pc laptop and handheld sizes. |
| `test_design_panel.py` | `test_merge_writes_the_values_in_place` |  |  | Only the values change: the layout, the comments and the rest of the file stay; the same variable under @media is not the panel's and stays; a key no rule defines is not in the keys returned. |
| `test_design_panel.py` | `test_the_panels_merge_is_pythons` |  | 0.2 s | Copy stylesheet in the browser and tools/apply_design.py give the same file: the panel's topRules() and merged() run in Node.js on the fixture above, against merge() here. |
| `test_design_panel.py` | `test_the_panel_offers_both_copies` |  |  | The panel offers both copies. |
| `test_design_panel.py` | `test_the_panel_keeps_its_own_colours_and_sizes` |  |  | A mock changes the site's variables and Material scales rem: the panel uses neither. |
| `test_disclaimer.py` | `test_sets_the_text_and_fills_the_marker` |  |  | Sets the text and fills the marker. |
| `test_disclaimer.py` | `test_every_disclaimer_has_the_same_text` |  |  | Every Disclaimer section in the repository's Markdown is the hook's text (owner, 28-10-2026: all disclaimers look the same): the marker on a wiki's home page, written out word for word everywhere else. |
| `test_disclaimer.py` | `test_every_wiki_uses_it` |  |  | Every wiki uses it. |
| `test_hang_limit.py` | `test_test_sh_limits_every_run` |  |  | Test sh limits every run. |
| `test_hang_limit.py` | `test_ci_limits_every_pytest_step` |  |  | Ci limits every pytest step. |
| `test_icons.py` | `test_installer_icon_exists` | 22 |  | Installer icon exists. |
| `test_icons.py` | `test_icon_copies_match_their_category` |  |  | Every copy in icons/categories.toml is its category's icon: run ../tools/sync_icons.py after changing icons/. |
| `test_icons.py` | `test_category_has_every_size` | 4 |  | WebP for Qt and the wiki; the 128 px one PNG, for menu entries, Steam and notifications. |
| `test_icons.py` | `test_every_app_icon_comes_from_a_category` |  |  | No app icon, portal tile or Big Picture category icon outside icons/categories.toml: one left there keeps an old icon. |
| `test_icons.py` | `test_portal_tabs_follow_the_icon_categories` |  |  | An app's tab in the portal (category in portal/apps.toml) is the category of its icon, and the portal knows every category of icons/ (owner, 27-10-2026: no Development tab; its development icon went with PS5 Installer Tests to dev/itests on 02-11-2026, where it takes Nexus's). |
| `test_installer_tests.py` | `test_every_app_has_an_installer_test` |  |  | Every app has an installer test. |
| `test_installer_tests.py` | `test_every_portal_entry_and_checkout_tool_has_an_installer_test` |  |  | Every portal entry and checkout tool has an installer test. |
| `test_installer_tests.py` | `test_every_installer_test_is_for_something_that_exists` |  |  | Every installer test is for something that exists. |
| `test_installer_tests.py` | `test_ci_runs_every_installer_test` |  | 0.1 s | CI's installers job runs the tools/installer-tests/*.sh its plan job names (tools/ci_matrix.py plan): every one it finds on a full run (stage 2, 04-11-2026: a new app's test runs without an edit to the workflow), the helper left out and the release tarballs last; no script is named in the workflow. |
| `test_instance_copies.py` | `test_copies_exist` |  |  | Copies exist. |
| `test_instance_copies.py` | `test_copy_matches_core` |  |  | Copy matches core. |
| `test_instance_copies.py` | `test_upstream_copy_matches_core` |  |  | Upstream copy matches core. |
| `test_instance_copies.py` | `test_theme_copy_matches_core` |  |  | Theme copy matches core. |
| `test_instance_copies.py` | `test_exit_keys_copy_matches_core` |  |  | Exit keys copy matches core. |
| `test_issue_templates.py` | `test_the_bug_reports_apps_are_the_manifests` |  |  | The bug reports apps are the manifests. |
| `test_layout.py` | `test_packages_sit_at_the_app_root` |  |  | apps/<name>/<package>/__main__.py, never apps/<name>/<folder>/<package>/__main__.py. |
| `test_layout.py` | `test_every_app_has_a_package_and_images_at_its_root` |  |  | Every app has a package and images at its root. |
| `test_layout.py` | `test_every_app_has_an_installer_at_its_root` |  |  | Every app has an installer at its root. |
| `test_layout.py` | `test_installers_take_the_standard_options_and_refuse_root` |  |  | --no-desktop-shortcut, --uninstall, --uninstall --purge, --help; run as your own user, not with sudo. |
| `test_layout.py` | `test_installers_upgrade_the_python_packages` |  |  | pip install -r with --upgrade: installing again brings each package to the newest version its requirements allow, a security fix within the range included (owner's decision, 13-10-2026). |
| `test_layout.py` | `test_the_suite_names_its_system` |  |  | The suite names its system. |
| `test_layout.py` | `test_the_tags_start_with_the_suites_prefix` |  |  | The suite's release tags are ps5-<app>-v<x.y.z> and ps5-portal-v<x.y.z> (owner, 15-11-2026): TAG_PREFIX says ps5-, every pin in apps.toml has it, and no app's key starts with it, so a tag names one app. |
| `test_layout.py` | `test_every_app_has_tests_and_ci_runs_them` |  | 0.1 s | Every app has tests and ci runs them. |
| `test_layout.py` | `test_the_dev_venv_installs_every_test_folders_requirements` |  |  | requirements-dev.txt at the root, the one venv of ./test.sh and the wiki, takes in the requirements-dev.txt of every folder with tests/. |
| `test_make_design.py` | `test_design_is_up_to_date` |  |  | Design is up to date. |
| `test_make_design.py` | `test_a_text_sample_sits_on_the_backdrop_it_reads_on` |  |  | A text sample sits on the backdrop it reads on. |
| `test_make_design.py` | `test_a_translucent_colour_shows_over_a_checkerboard` |  |  | A translucent colour shows over a checkerboard. |
| `test_make_design.py` | `test_every_colour_of_the_wikis_is_listed` |  |  | Every colour of the wikis is listed. |
| `test_make_design.py` | `test_unlisted_reports_both_directions` |  |  | Unlisted reports both directions. |
| `test_make_design.py` | `test_check_lists_changed_and_unused_samples` |  |  | Check lists changed and unused samples. |
| `test_mkdocs_hooks.py` | `test_webp_copy_keeps_the_picture` |  |  | Webp copy keeps the picture. |
| `test_mkdocs_hooks.py` | `test_pages_point_at_the_copies_only` |  |  | Pages point at the copies only. |
| `test_mkdocs_hooks.py` | `test_only_pictures_a_page_names_are_converted` |  |  | Only pictures a page names are converted. |
| `test_mkdocs_hooks.py` | `test_every_app_chapter_shows_its_icon` |  |  | An app's chapter starts with the app's icon beside its heading (two chapters once lacked it). |
| `test_mkdocs_hooks.py` | `test_every_wiki_page_starts_with_an_icon_or_a_symbol` |  |  | Every page of the wiki starts with an app's icon or a symbol (a page-icon) above its heading (owner, 15-11-2026); the Home page starts with its pictures. |
| `test_new_app.py` | `test_defaults` |  |  | Defaults. |
| `test_new_app.py` | `test_writes_the_app_and_lists_it_everywhere` |  | 0.1 s | Writes the app and lists it everywhere. |
| `test_new_app.py` | `test_names_are_the_owners` |  | 0.1 s | Names are the owners. |
| `test_new_app.py` | `test_refusals` | 5 |  | Refusals. |
| `test_new_app.py` | `test_a_folder_without_a_portal_is_refused` |  |  | A folder without a portal is refused. |
| `test_new_app.py` | `test_the_help_names_the_steps` |  | 0.1 s | The help names the steps. |
| `test_new_app.py` | `test_a_nav_by_category_gets_the_app_under_its_category_by_name` |  |  | The wiki lists the apps by category, by name in each: a new app's line goes where its name belongs. |
| `test_pin_app.py` | `test_pin_changes_only_that_app` |  |  | Pin changes only that app. |
| `test_pin_app.py` | `test_pin_last_table_and_missing_app` |  |  | Pin last table and missing app. |
| `test_pin_app.py` | `test_pin_adds_the_sha256_line_a_new_app_lacks` |  |  | A new app is listed with its first tag and no sha256 line until that release exists (apps.toml allows it): the pin adds the line after the tag, in its place, and leaves the rest alone. |
| `test_pin_app.py` | `test_main_writes_the_manifest` |  |  | A pin from the command line writes the tag and sha256 lines of portal/apps.toml. |
| `test_portal_icons.py` | `test_the_portal_tile_is_the_suites_icon` |  |  | portal.webp is the suite's own icon, by its pixels at 32 px as below; the other tiles are category icons (tests/test_icons.py). |
| `test_portal_icons.py` | `test_the_wiki_icon_is_the_portals` |  |  | The wiki's logo and favicon (docs/images/wiki-icon.*) are scaled copies of the portal's icon, so they are compared by their pixels at 32 px: they lagged once after the icon changed (seen 16-10-2026). |
| `test_portal_screenshot.py` | `test_the_picture_is_written_and_the_tool_exits_cleanly` |  | 1.1 s | The tool deletes the window and the application itself, in order, once the picture is saved (03-11-2026: left to the interpreter's exit, the process crashed now and then on the wiki's runner after the picture was written). |
| `test_portal_tour_stamp.py` | `test_the_wikis_portal_tour_was_recorded_from_this_portal` |  |  | The wikis portal tour was recorded from this portal. |
| `test_portal_tour_stamp.py` | `test_the_fingerprint_follows_the_portal_but_not_its_version` |  |  | The fingerprint follows the portal but not its version. |
| `test_portal_tour_stamp.py` | `test_the_fingerprint_follows_the_tiles_but_not_the_pins` |  |  | New tiles need a new video (owner, 15-11-2026); a release, which only moves tags and checksums, does not. |
| `test_publish_release.py` | `test_a_new_release_is_published_with_its_tag_on_the_commit` |  |  | A new release is published with its tag on the commit. |
| `test_publish_release.py` | `test_an_app_release_is_never_latest` |  |  | An app release is never latest. |
| `test_publish_release.py` | `test_a_draft_run_makes_a_draft` |  |  | A draft run makes a draft. |
| `test_publish_release.py` | `test_a_draft_there_already_is_made_anew` |  |  | A draft there already is made anew. |
| `test_publish_release.py` | `test_a_release_out_already_is_left_alone_by_a_draft_run` |  |  | A release out already is left alone by a draft run. |
| `test_publish_release.py` | `test_a_tag_pushed_again_uploads_the_assets_again` |  |  | A tag pushed again uploads the assets again. |
| `test_readme_badges.py` | `test_every_readme_has_the_three_badges` |  |  | Every readme has the three badges. |
| `test_release_commit.py` | `test_a_release_commit_as_the_nexus_release_tool_writes_it` |  | 0.1 s | A release commit as the nexus release tool writes it. |
| `test_release_commit.py` | `test_anything_more_is_not_a_release_commit` | 12 | 0.9 s | Anything more is not a release commit. |
| `test_release_commit.py` | `test_a_changed_file_that_holds_no_version_copy` |  | 0.1 s | A changed file that holds no version copy. |
| `test_release_commit.py` | `test_a_merge_or_an_unknown_parent_is_not` |  | 0.1 s | A merge or an unknown parent is not. |
| `test_script_help.py` | `test_help_is_the_header_comment` |  |  | Help is the header comment. (Skipped here.) |
| `test_script_help.py` | `test_the_tools_scripts_print_their_header_as_help` | 5 |  | tools/*.sh with --help print the comment under the SPDX line, and do nothing else. |
| `test_script_help.py` | `test_the_release_and_tour_scripts_have_help` |  |  | The release and tour scripts have help. |
| `test_stage.py` | `test_readme_and_wiki_follow_the_portal_stage` |  |  | Readme and wiki follow the portal stage. |
| `test_stage_app.py` | `test_stage_keeps_sources_and_drops_build_output` |  |  | Stage keeps sources and drops build output. |
| `test_stage_app.py` | `test_uses_core_stays_out_of_the_skipped_folders` |  |  | cargo's target is not walked: its folders come and go during a build, and one that was gone failed the walk. |
| `test_suite_release.py` | `test_a_tag_pushed_by_hand_is_that_release_published_at_once` |  |  | A tag pushed by hand is that release published at once. |
| `test_suite_release.py` | `test_a_nexus_release_brings_the_unreleased_pins_and_a_draft_portal` |  |  | A nexus release brings the unreleased pins and a draft portal. |
| `test_suite_release.py` | `test_a_withdrawn_app_is_not_built` |  |  | A withdrawn app is not built. |
| `test_suite_release.py` | `test_a_portal_out_already_releases_nothing_but_apps_need_a_bump` |  |  | A portal out already releases nothing but apps need a bump. |
| `test_suite_release.py` | `test_only_the_portal_a_withdrawal_for_instance` |  |  | Only the portal a withdrawal for instance. |
| `test_suite_release.py` | `test_pin_sets_only_the_sha256_line_of_that_app` |  |  | Pin sets only the sha256 line of that app. |
| `test_suite_release.py` | `test_pin_refuses_a_tag_the_manifest_does_not_pin` |  |  | Pin refuses a tag the manifest does not pin. |
| `test_suite_release.py` | `test_the_checksum_comes_from_the_releases_own_sha256sums` |  |  | The checksum comes from the releases own sha256sums. |
| `test_suite_release.py` | `test_pin_on_the_command_line` |  |  | Pin on the command line. |
| `test_suite_release.py` | `test_the_published_releases_come_from_one_listing` |  |  | One gh release list for the plan, not a gh release view per pinned app; a draft is not out. |
| `test_suite_release.py` | `test_without_a_whole_listing_the_tags_are_asked_one_by_one` |  |  | GitHub does not answer, answers something else, or the listing is full (a release could be missing from it, and would be built again): no set, so the plan asks tag by tag. |
| `test_suites.py` | `test_the_system_and_the_prefix` |  |  | The system and the prefix. |
| `test_suites.py` | `test_a_tag_names_its_app_and_version` |  |  | A tag names its app and version. |
| `test_suites.py` | `test_the_command_line` |  | 0.1 s | This repository is the suite. |
| `test_sync_icons.py` | `test_category_icons_need_no_conversion` |  | 0.1 s | Category icons need no conversion. |
| `test_sync_icons.py` | `test_an_image_by_another_name_becomes_every_size` |  | 0.2 s | An image by another name becomes every size. |
| `test_sync_icons.py` | `test_an_image_named_by_its_size_replaces_only_that_size` |  | 0.1 s | leaf-512.png becomes leaf-512.webp; a 128 px PNG at the wrong size is scaled in place; the rest stays. |
| `test_sync_icons.py` | `test_a_size_of_its_own_wins_over_the_whole_set` |  | 0.2 s | A size of its own wins over the whole set. |
| `test_sync_icons.py` | `test_two_images_for_every_size_are_refused` |  | 0.1 s | Two images for every size are refused. |
| `test_sync_icons.py` | `test_a_wide_image_is_refused` |  | 0.1 s | A wide image is refused. |
| `test_sync_icons.py` | `test_from_converts_the_sizes_named_and_writes_the_copies` |  | 0.1 s | From converts the sizes named and writes the copies. |
| `test_sync_icons.py` | `test_from_options_that_do_not_go_together_are_refused` | 5 | 0.3 s | From options that do not go together are refused. |
| `test_sync_icons.py` | `test_root_picks_the_suite_and_one_without_category_icons_is_refused` |  | 0.1 s | The default is the checkout; --root names a suite folder anywhere (tools/new_app.py). |
| `test_sync_icons.py` | `test_the_suite_is_in_step` |  |  | The suite is in step. |
| `test_sync_icons.py` | `test_check_lists_what_is_not_converted` |  | 0.1 s | Check lists what is not converted. |
| `test_tag_release.py` | `test_refuses_a_bump_that_is_not_committed` |  | 0.1 s | Refuses a bump that is not committed. |
| `test_tag_release.py` | `test_refuses_a_new_app_that_is_not_committed` |  | 0.1 s | The owner's case of 29-10-2026: a shadps4-v0.1.0, staged but not committed, ended in a bare exit 128. |
| `test_tag_release.py` | `test_refuses_an_unpushed_bump_then_tags_the_pushed_one` |  | 0.4 s | Refuses an unpushed bump then tags the pushed one. |
| `test_tag_release.py` | `test_checks_every_tag_before_tagging_any` |  | 0.3 s | Checks every tag before tagging any. |
| `test_tag_release.py` | `test_tags_only_a_commit_ci_passed` |  | 0.6 s | Tags only a commit ci passed. |
| `test_tag_release.py` | `test_a_portal_tag_waits_for_the_app_releases_it_pins` |  | 0.6 s | The portal release that failed: tagged with an app release that was not tagged yet, pinned without sha256. |
| `test_tag_release.py` | `test_help_and_a_tag_without_the_prefix` |  | 0.1 s | Help and a tag without the prefix. |
| `test_wiki_apps.py` | `test_every_app_has_a_chapter_and_no_chapter_is_left_over` |  |  | Every app has a chapter and no chapter is left over. |
| `test_wiki_apps.py` | `test_the_overviews_list_exactly_the_apps` |  |  | The app overviews by each app's name; the home page links every app, by a name of its own. |
| `test_wiki_apps.py` | `test_the_navigation_and_the_readme_name_every_app` |  |  | The navigation and the readme name every app. |
| `test_wiki_apps.py` | `test_the_navigation_lists_the_apps_by_category_in_alphabetical_order` |  |  | A header per category under Apps, each with its apps by name; a category without an app says Coming soon. |
| `test_wiki_apps.py` | `test_the_install_page_names_a_portal_release` |  |  | The hook writes the newest published portal's tag where the page says {{ portal_tag }}. |
| `test_wiki_designs.py` | `test_there_is_the_wiki` |  |  | There is the wiki. |
| `test_wiki_designs.py` | `test_a_wiki_stands_on_its_own` |  |  | A wiki stands on its own. |
| `test_wiki_designs.py` | `test_no_stylesheet_is_shared` |  |  | No stylesheet is shared. |
| `test_wiki_designs.py` | `test_every_variable_is_labelled` |  |  | Every variable is labelled. |
| `test_wiki_designs.py` | `test_every_colour_is_a_variable` |  |  | A color written anywhere but in a variable could not be changed in the design panel. |
| `test_wiki_designs.py` | `test_the_header_has_variables_of_its_own` |  |  | The header's background and text are what the panel changes for the header, in each wiki: the text is the name beside the icon (the wiki) or the links alone (the Nexus page, whose icon carries the name). |
