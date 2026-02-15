import json
import re

# todo: ad5x / screen exclusive set values

# zmod_settings.json structure:
# "Categories": A set of key-value pairs for the categories settings are divided into.
#               The keys are purely for internal use. The values specify category texts.
#       "get_zmod_data_text": String. Text displayed as the header for this category in GET_ZMOD_DATA results.
#       "global_text": String. Text displayed as the header for this category in GLOBAL results. If not specified, will
#                      use get_zmod_data_text for GLOBAL too.
#
# "Settings": A set of key-value pairs for the actual parameters. The keys should match the parameter name.
#       "type": The type of data stored by the setting (int, string, etc). Assumed type if not specified is indicated by
#               TYPE_ASSUMPTION. If set to "special", the parameter will do nothing in SAVE/GET_ZMOD_DATA or _RESET_ZMOD,
#               and in GLOBAL will copy pre-written code exactly. (Used for LANG and _RESET_ZMOD buttons.)
#       "default": The default value for the parameter. Assumed default if not specified is the value of
#                  DEFAULT_STRING_ASSUMPTION for strings, or DEFAULT_VALUE_ASSUMPTION for anything else.
#       "category": The category for the parameter (should match one of the keys from Categories).
#       "show_condition": Additional condition(s) that need to be met for this parameter to be visible in GET_ZMOD_DATA or
#                         GLOBAL. Note that this does not affect SAVE_ZMOD_DATA or _RESET_ZMOD. The value is copied verbatim
#                         into a {% if ... %} in the output cfg file. You can reference the value of parameters in earlier
#                         categories, or earlier parameters in the same category, by prefixing their name with a z, so for
#                         example, you could write "zuse_trash_on_print == 0" to only show the option if USE_TRASH_ON_PRINT
#                         is set to zero.
#       "show_in_global": Whether or not the parameter shows up in GLOBAL. Defaults to true if not specified.
#       "require_native_screen": Set whether the setting requires a certain native screen state. 1 for only show if native
#                                screen is on, -1 for only if it's off, 0 for always show. Default is always show.
#       "require_ad5x": Same, but 1 for AD5X, -1 for AD5M/Pro, 0 for all. Default is always show.
#       "get_zmod_data_text": Key-value pairs to set the text for GET_ZMOD_DATA corresponding to the various values for
#                             the setting. For non-string-value settings, "n" can be added at the end of the value to
#                             specify a different text on native screen, or "x" for different text on AD5X. If doing this,
#                             the order in the value (eg. "1nx" vs "1xn") doesn't matter, but the text with the n / x must
#                             come before the one without it. A value of "*" can also be specified; this will be used if
#                             no other value is matched. It must be the last entry, and cannot have n/x qualifiers. To
#                             reference the user's current value of the setting in your text, use the setting name prefixed
#                             with a z (eg. to show the raw value of USE_TRASH_ON_PRINT, put {zuse_trash_on_print}).
#       "get_global_text": Same, but for GLOBAL. If absent, get_zmod_data_text values will be used for GLOBAL. If using a
#                          seperate get_global_text, it must specify every value (ie: fallback to get_zmod_data_text is
#                          all-or-nothing).
#       "global_set_values": A list of values that will be cycled through when using the GLOBAL menu to change the setting.
#                            If absent, the values from get_global_text will be used (including the get_zmod_data_text
#                            fallback, where applicable). This is generally useful for numeric parameters (eg. LED) or
#                            when it is not desirable to have every possible setting exposed in GLOBAL but you still want
#                            to provide texts for the setting.
#       "global_set_values_ad5x": If present, overrides global_set_values when on the AD5X.
#       "global_set_values_native_screen": If present, overrides global_set_values and global_set_values_ad5x when the native
#                                          screen is enabled.
#       "global_set_values_native_screen_ad5x": If present, overrides the other global_set_values params when the native screen
#                                               is enabled on an AD5X.
#       "code": This is only used if the type is set to special. The contents of this will be copied verbatim into the output
#               cfg file. This is used for buttons that need special handling like LANG and _RESET_ZMOD's buttons.


STANDARD_INDENT = '    '
BASE_INDENT_SAVE_ZMOD_DATA = 1
BASE_INDENT_GET_ZMOD_DATA = 1
BASE_INDENT_RESET_ZMOD = 1
BASE_INDENT_GLOBAL = 1

ITEMS_PER_GLOBAL_PAGE = 4

DEFAULT_VALUE_ASSUMPTION = 0
DEFAULT_STRING_ASSUMPTION = ""
TYPE_ASSUMPTION = 'int'

GLOBAL_CANNOT_CHANGE_COLOR = 'grey'

def get_setting_global_settable_options(setting, is_ad5x, is_native_screen):
    texts = setting.get("global_text", None)
    if texts == None:
        texts = setting.get("get_zmod_data_text", {})
    
    can_set_values = setting.get("global_set_values", None)
    if is_ad5x:
        can_set_values = setting.get("global_set_values_ad5x", can_set_values)
    if is_native_screen:
        can_set_values = setting.get("global_set_values_native_screen", can_set_values)
    if is_ad5x and is_native_screen:
        can_set_values = setting.get("global_set_values_native_screen_ad5x", can_set_values)
    if can_set_values == None:
        can_set_values = []
        for condition, _ in texts.items():
            if condition == '*':
                break
            if setting.get('type', TYPE_ASSUMPTION) != 'string':
                condition = re.sub(r'[nx]', '', condition)
            can_set_values += [condition]
            
    can_set_values = [str(value) for value in can_set_values]
        
    return list(dict.fromkeys(can_set_values))

def get_all_setting_global_settable_options(setting):
    ad5m_guppy = get_setting_global_settable_options(setting, False, False)
    ad5m_native = get_setting_global_settable_options(setting, False, True)
    ad5x_guppy = get_setting_global_settable_options(setting, True, False)
    ad5x_native = get_setting_global_settable_options(setting, True, True)
    merged_list = ad5m_guppy + ad5m_native + ad5x_guppy + ad5x_native
    
    return list(dict.fromkeys(merged_list))
    

def get_setting_global_options(setting_name, setting, is_ad5x, is_native_screen):
    result = []
    
    texts = setting.get("global_text", None)
    if texts == None:
        texts = setting.get("get_zmod_data_text", {})
    
    can_set_values = get_setting_global_settable_options(setting, is_ad5x, is_native_screen)
    done_conditions = []
    
    generic_text = texts.get('*', None)
    
    for value in can_set_values:
        next_value_index = can_set_values.index(value) + 1
        if next_value_index == len(can_set_values):
            next_value_index = 0
        next_value = can_set_values[next_value_index]
        
        for condition, text in texts.items():
            if setting['type'] != 'string':
                condition_ad5x = 'x' in condition
                condition_native_screen = 'n' in condition
                condition_stripped = re.sub(r'[nx]', '', condition)
            else:
                condition_ad5x = False
                condition_native_screen = False
                condition_stripped = condition
                
            if condition_stripped != value:
                continue
                
            if condition_ad5x and not is_ad5x:
                continue
            if condition_native_screen and not is_native_screen:
                continue
            
            result += [{
                "condition": condition_stripped,
                "text": text,
                "next_value": next_value
            }]
            done_conditions += [condition_stripped]
            break
        if value not in done_conditions:
            if generic_text == None:
                option_text = f"{setting_name.upper()} ===custom value:=== {{z{setting_name.lower()}}}"
            else:
                option_text = generic_text
            result += [{
                "condition": value,
                "text": option_text,
                "next_value": next_value
            }]

    for condition, text in texts.items():
        if setting['type'] != 'string':
            condition_ad5x = 'x' in condition
            condition_native_screen = 'n' in condition
            condition_stripped = re.sub(r'[nx]', '', condition)
        else:
            condition_ad5x = False
            condition_native_screen = False
            condition_stripped = condition
            
        if condition_stripped in done_conditions:
            continue
            
        if condition_ad5x and not is_ad5x:
            continue
        if condition_native_screen and not is_native_screen:
            continue
        
        result += [{
            "condition": condition_stripped,
            "text": text,
            "next_value": None
        }]
        
        if condition_stripped == '*':
            break
        done_conditions += [condition_stripped]
        
    return result

def add_save_zmod_data(file_data, categories, settings):
    indent_level = BASE_INDENT_SAVE_ZMOD_DATA

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated SAVE_ZMOD_DATA code')
    file_data.append('')

    for category, cat_data in categories.items():
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue

            if set_data.get('require_ad5x', 0) != 0:
                if set_data.get('require_ad5x', 0) > 0:
                    file_data.append((indent_level * STANDARD_INDENT) + "{% if client.ad5x %}")
                else:
                    file_data.append((indent_level * STANDARD_INDENT) + "{% if not client.ad5x %}")
                indent_level += 1

            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if params.{setting.upper()} %}}")
            indent_level += 1

            if set_data.get('type', TYPE_ASSUMPTION) == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = params.{setting.upper()}|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% if z{setting.lower()} == \"0\" %}}")
                file_data.append(((indent_level + 1) * STANDARD_INDENT) + f"{{% set z{setting.lower()} = \"\" %}}")
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"\\\"{{z{setting.lower()}}}\\\"\"")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting} = params.{setting.upper()}|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{set_data.get('type', TYPE_ASSUMPTION)} %}}")
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={{z{setting.lower()}}}")

            indent_level -= 1
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

            if set_data.get('require_ad5x', 0) != 0:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

            file_data.append('')

    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated SAVE_ZMOD_DATA code')

def add_get_zmod_data(file_data, categories, settings):
    indent_level = BASE_INDENT_GET_ZMOD_DATA

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated GET_ZMOD_DATA code')
    file_data.append('')

    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"info\" MSG=\"{cat_data.get("get_zmod_data_text", "")}\"")
        file_data.append('')
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue

            if set_data.get('require_ad5x', 0) != 0 or set_data.get('require_native_screen', 0) != 0:
                if set_data.get('require_ad5x', 0) != 0 and set_data.get('require_native_screen', 0) != 0:
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {"not " if set_data.get('require_ad5x', 0) < 0 else ""}client.ad5x and screen == {"true" if set_data.get('require_native_screen', 0) > 0 else "false"} %}}")
                elif set_data.get('require_ad5x', 0) != 0:
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {"not " if set_data.get('require_ad5x', 0) < 0 else ""}client.ad5x %}}")
                else: # require_native_screen != 0 is implied
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if screen == {"true" if set_data.get('require_native_screen', 0) > 0 else "false"} %}}")
                indent_level += 1

            condition = set_data.get('show_condition', None)
            if condition != None:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {condition} %}}")
                indent_level += 1
            setting_type = set_data.get('type', TYPE_ASSUMPTION)

            if setting_type == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}']|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}']|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{setting_type} %}}")

            had_generic = False
            is_first = True
            for text_condition, text in set_data.get('get_zmod_data_text', {}).items():
                if text_condition == '*':
                    had_generic = True
                    if not is_first:
                        file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                else:
                    had_regular = True
                    prefix = "" if is_first else "el" # "if" or "elif"

                    if not is_first:
                        indent_level -= 1

                    check_5x = False
                    check_native_screen = False

                    if setting_type != 'string':
                        if 'n' in text_condition:
                            check_native_screen = True
                        if 'x' in text_condition:
                            check_5x = True
                        text_condition = re.sub(r'[nx]', '', text_condition)

                    condition_string = f"{prefix}if z{setting.lower()} == "

                    if setting_type == 'string':
                        condition_string += f"\"{text_condition}\""
                    else:
                        condition_string += f"{text_condition}"

                    if check_native_screen:
                        condition_string += " and screen == True"

                    if check_5x:
                        condition_string += " and client.ad5x"

                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% {condition_string} %}}")
                    indent_level += 1

                if setting_type == 'string':
                    file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"//\" MSG=\"{text} // SAVE_ZMOD_DATA {setting.upper()}=\\\"{{z{setting.lower()}}}\\\"\"")
                else:
                    file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"//\" MSG=\"{text} // SAVE_ZMOD_DATA {setting.upper()}={{z{setting.lower()}}}\"")

                if had_generic:
                    break

                is_first = False

            if not had_generic:
                if not is_first:
                    file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                if setting_type == 'string':
                    file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"//\" MSG=\"===Unrecognized value for setting:=== {setting.upper()} // SAVE_ZMOD_DATA {setting.upper()}=\\\"{{z{setting.lower()}}}\\\"\"")
                else:
                    file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"//\" MSG=\"===Unrecognized value for setting:=== {setting.upper()} // SAVE_ZMOD_DATA {setting.upper()}={{z{setting.lower()}}}\"")

            if not is_first or not had_generic:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

            if setting_type == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"\\\"{{z{setting.lower()}}}\\\"\"")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={{z{setting.lower()}}}")

            if condition != None:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

            if set_data.get('require_ad5x', 0) != 0 or set_data.get('require_native_screen', 0) != 0:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

            file_data.append('')

    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated GET_ZMOD_DATA code')

def add_reset_zmod(file_data, categories, settings):
    indent_level = BASE_INDENT_RESET_ZMOD

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated _RESET_ZMOD code')
    file_data.append('')

    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"# {category}")
        both_entries = []
        ad5m_entries = []
        ad5x_entries = []
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
            if set_data.get('exclude_from_reset', False):
                continue
            if not set_data.get('show_in_global', True):
                continue
            check_ad5x = set_data.get('require_ad5x', 0)
            if check_ad5x < 0:
                target = ad5m_entries
                extra_indent = 1
            elif check_ad5x > 0:
                target = ad5x_entries
                extra_indent = 1
            else:
                target = both_entries
                extra_indent = 0
                
            settable_values = get_all_setting_global_settable_options(set_data)
            
            if len(settable_values) == 0:
                continue
            
            setting_type = set_data.get('type', TYPE_ASSUMPTION)
            quotechar = '"' if setting_type == 'string' else ''
            
            target.append(((indent_level + extra_indent) * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}'] %}}")
            
            if_line = None
            for settable_value in settable_values:
                if if_line == None:
                    if_line = "{% if"
                else:
                    if_line += " or"
                if_line += f" z{setting.lower()} == {quotechar}{settable_value}{quotechar}"
                
            if_line += " %}"
            
            target.append(((indent_level + extra_indent) * STANDARD_INDENT) + if_line)

            if setting_type == 'string':
                target.append((((indent_level + 1) + extra_indent) * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"\\\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\\\"\"")
            else:
                target.append((((indent_level + 1) + extra_indent) * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={set_data.get('default', DEFAULT_VALUE_ASSUMPTION)}")
                
            target.append(((indent_level + extra_indent) * STANDARD_INDENT) + "{% endif %}")
            target.append('')

        file_data += both_entries

        if len(ad5m_entries) > 0:
            file_data.append((indent_level * STANDARD_INDENT) + "{% if not client.ad5x %}")
            file_data += ad5m_entries
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

        if len(ad5x_entries) > 0:
            file_data.append((indent_level * STANDARD_INDENT) + "{% if client.ad5x %}")
            file_data += ad5x_entries
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

        file_data.append('')

    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated _RESET_ZMOD code')


def add_global(file_data, categories, settings):
    indent_level = BASE_INDENT_GLOBAL

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated _GLOBAL code')
    file_data.append('')

    # This one is trickier. We need some extra logic here to skip unused pages, and divide into pages.
    # To make this easier and tidier, we:
    # -- Make four seperate lists altogether, for each combination of AD5M/AD5X and native screen on/off
    # -- Create a list of settings to include, then generate the menus from that

    for is_native_screen in [True, False]:
        for is_ad5x in [True, False]:
            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {"" if is_ad5x else "not "}client.ad5x and screen == {"True" if is_native_screen else "False"} %}}")
            indent_level += 1

            setting_entries = []

            for category, cat_data in categories.items():
                category_entries = {}
                header_text = cat_data.get("global_text", None)
                if header_text == None:
                    header_text = cat_data.get("get_zmod_data_text", "")
                setting_entries += [{"header": header_text, "settings": category_entries}]

                for setting, set_data in settings.items():
                    if set_data.get('category', '') != category:
                        continue
                    if set_data.get('require_native_screen', 0) > 0 and not is_native_screen:
                        continue
                    if set_data.get('require_native_screen', 0) < 0 and is_native_screen:
                        continue
                    if set_data.get('require_ad5x', 0) > 0 and not is_ad5x:
                        continue
                    if set_data.get('require_ad5x', 0) < 0 and is_ad5x:
                        continue
                    if set_data.get('show_in_global', True) == False:
                        continue
                    category_entries[setting] = set_data

            page = 1
            items_on_page = 0

            indent_level += 1

            for category_entry in setting_entries:
                for setting, set_data in category_entry['settings'].items():
                    if items_on_page == ITEMS_PER_GLOBAL_PAGE:
                        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_footer_button ===Next===|_GLOBAL N={page + 1}|red\"")
                        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_show\"")
                        file_data.append((indent_level * STANDARD_INDENT) + "{% if this_page_visible_items == 0 %}")
                        file_data.append(((indent_level + 1) * STANDARD_INDENT) + "RESPOND TYPE=command MSG=\"action:prompt_end\"")
                        file_data.append(((indent_level + 1) * STANDARD_INDENT) + "_GLOBAL N={page+1}")
                        file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                        file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% endif %}")
                        file_data.append('')

                        page += 1
                        items_on_page = 0
                    if items_on_page == 0:
                        file_data.append(((indent_level - 1) * STANDARD_INDENT) + f"{{% if n == {page} and start == 0 %}}")
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% set this_page_visible_items = 0 %}}")
                        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_begin Page {page} : {category_entry['header']}\"")
                        file_data.append('')

                    setting_type = set_data.get('type', TYPE_ASSUMPTION)

                    if setting_type == "special":
                        code = set_data.get('code', '').replace('\r', '').split('\n')
                        file_data.append((indent_level * STANDARD_INDENT) + "{% set this_page_visible_items = this_page_visible_items + 1 %}")
                        for line in code:
                            file_data.append((indent_level * STANDARD_INDENT) + line)
                        file_data.append('')
                        items_on_page += 1
                    else:
                        extra_condition = set_data.get('show_condition', None)
                        if extra_condition != None:
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {extra_condition} %}}")
                            indent_level += 1

                        if setting_type == 'string':
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}']|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
                        else:
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}']|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{setting_type} %}}")

                        setting_conditions = get_setting_global_options(setting, set_data, is_ad5x, is_native_screen)                            
                        
                        if len(setting_conditions) == 0:
                            file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {setting.upper()} ===custom value:=== {{z{setting.lower()}}}|_GLOBAL N={page}|{GLOBAL_CANNOT_CHANGE_COLOR}\"")
                        elif len(setting_conditions) == 1 and setting_conditions[0]['condition'] == '*':
                            file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {setting_conditions[0]['text']}|_GLOBAL N={page}|{GLOBAL_CANNOT_CHANGE_COLOR}\"")
                        else:
                            generic_option = setting_conditions[-1]
                            if generic_option['condition'] == '*':
                                setting_conditions.remove(generic_option)
                            else:
                                generic_option = None
                            if_text = 'if'
                            for this_condition in setting_conditions:
                                local_condition = this_condition['condition']
                                if setting_type == 'string':
                                    local_condition = f"\"{local_condition}\""
                                file_data.append((indent_level * STANDARD_INDENT) + f"{{% {if_text} z{setting} == {local_condition} %}}")
                                if_text = 'elif'
                                if this_condition['next_value'] == None:
                                    file_data.append(((indent_level + 1) * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {this_condition['text']}|_GLOBAL N={page}|{GLOBAL_CANNOT_CHANGE_COLOR}\"")
                                else:
                                    local_next_value = this_condition['next_value']
                                    if setting_type == 'string':
                                        local_next_value = f"\\\"{local_next_value}\\\""
                                    file_data.append(((indent_level + 1) * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {this_condition['text']}|SAVE_ZMOD_DATA {setting.upper()}={local_next_value} I={page}|primary\"")
                            
                            file_data.append((indent_level * STANDARD_INDENT) + "{% else %}")
                            
                            if generic_option == None:
                                fallback_text = f"{setting.upper()} ===custom value:=== {{z{setting.lower()}}}"
                            else:
                                fallback_text = generic_option['text']
                                
                            file_data.append(((indent_level + 1) * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {fallback_text}|_GLOBAL N={page}|{GLOBAL_CANNOT_CHANGE_COLOR}\"")
                            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                            
                        file_data.append((indent_level * STANDARD_INDENT) + "{% set this_page_visible_items = this_page_visible_items + 1 %}")

                        if extra_condition != None:
                            indent_level -= 1
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% endif %}}")

                        file_data.append('')
                        items_on_page += 1

                if items_on_page > 0:
                    items_on_page = ITEMS_PER_GLOBAL_PAGE # force page change between categories

            if items_on_page > 0:
                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_footer_button ===Next===|_GLOBAL N={page + 1}|red\"")
                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_show\"")
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                file_data.append('')
                page += 1

            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if n >= {page} and start == 0 %}}")
            file_data.append(((indent_level + 1) * STANDARD_INDENT) + "_SHOW_MSG MSG=\"===If any parameters were changed, it is recommended to reboot the printer===. Macro GLOBAL\" COMMAND='_GLOBAL_SAVE PARAM=skip_global' COMMAND_REBOOT=\"_GLOBAL_SAVE PARAM=skip_global REBOOT=1\"")
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")

            indent_level -= 1
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")


    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated _GLOBAL code')
    file_data.append('')

def main():
    with open('zmod_settings.json', 'r', encoding='utf-8') as f:
        settings_json_data = json.load(f)

    categories = settings_json_data['Categories']
    settings = settings_json_data['Settings']

    file_data = []

    with open('../base.cfg', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('# **'):
                if line.strip() == '# ** SAVE_ZMOD_DATA ** #':
                    add_save_zmod_data(file_data, categories, settings)
                if line.strip() == '# ** GET_ZMOD_DATA ** #':
                    add_get_zmod_data(file_data, categories, settings)
                if line.strip() == '# ** _RESET_ZMOD ** #':
                    add_reset_zmod(file_data, categories, settings)
                if line.strip() == '# ** _GLOBAL ** #':
                    add_global(file_data, categories, settings)
            else:
                file_data += [line]

    with open('../base.cfg.tmp', 'w', encoding='utf-8') as f:
        for line in file_data:
            f.write(line)
            if not line.endswith('\n'):
                f.write('\n')

if __name__ == "__main__":
    main()