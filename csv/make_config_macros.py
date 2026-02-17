import json
import re

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
#                             the setting. For non-string-value settings, certain characters can be appended to make the
#                             text only apply to certain situations:
#                               n - only show when using native screen
#                               g - only show when using GuppyScreen / no screen
#                               x - only show on AD5X
#                               m - only show on AD5M / AD5M Pro
#                             Also, the last entry can have a value of "*". This will specify a custom text when the user's
#                             setting does not match any of the available options. The value of the setting can be referenced
#                             with the setting name prefixed with z, eg: {zuse_trash_on_print}
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
#       "min_valid_value": If present, values below this will be rejected.
#       "max_valid_value": Same, but for maximum.
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

def validate_setup(ad5x_requirement, native_screen_requirement, is_ad5x, is_native_screen):
    if ad5x_requirement < 0 and is_ad5x:
        return False
    if ad5x_requirement > 0 and not is_ad5x:
        return False
    if native_screen_requirement < 0 and is_native_screen:
        return False
    if native_screen_requirement > 0 and not is_native_screen:
        return False
    return True

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
                if 'n' in condition and not is_native_screen:
                    continue
                if 'g' in condition and is_native_screen:
                    continue
                if 'x' in condition and not is_ad5x:
                    continue
                if 'm' in condition and is_ad5x:
                    continue
                condition = re.sub(r'[nxmg]', '', condition)
            can_set_values += [condition]

    can_set_values = [str(value) for value in can_set_values]

    return list(dict.fromkeys(can_set_values))
    
def get_valid_options(setting, is_ad5x, is_native_screen):
    global_options = get_setting_global_options('placeholder', setting, is_ad5x, is_native_screen)
    global_options = [option['condition'] for option in global_options]
    
    result = {
        'settable_values': get_setting_global_settable_options(setting, is_ad5x, is_native_screen),
        'valid_values': global_options,
        'min_value': setting.get('min_valid_value', None),
        'max_value': setting.get('max_valid_value', None),
        'allow_generic': '*' in global_options
    }
    
    if '*' in global_options:
        global_options.remove('*')
        
    return result    

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
                condition_ad5x = 1 if 'x' in condition else -1 if 'm' in condition else 0
                condition_native_screen = 1 if 'n' in condition else -1 if 'g' in condition else 0
                condition_stripped = re.sub(r'[nxmg]', '', condition)
            else:
                condition_ad5x = False
                condition_native_screen = False
                condition_stripped = condition

            if condition_stripped != value:
                continue
                
            if not validate_setup(condition_ad5x, condition_native_screen, is_ad5x, is_native_screen):
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
            condition_ad5x = 1 if 'x' in condition else -1 if 'm' in condition else 0
            condition_native_screen = 1 if 'n' in condition else -1 if 'g' in condition else 0
            condition_stripped = re.sub(r'[nxmg]', '', condition)
        else:
            condition_ad5x = False
            condition_native_screen = False
            condition_stripped = condition

        if condition_stripped in done_conditions:
            continue

        if not validate_setup(condition_ad5x, condition_native_screen, is_ad5x, is_native_screen):
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

def add_save_zmod_data(file_data, is_ad5x, is_native_screen, categories, settings):
    indent_level = BASE_INDENT_SAVE_ZMOD_DATA

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated SAVE_ZMOD_DATA code')
    file_data.append('')

    for category, cat_data in categories.items():
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
                
            if not validate_setup(set_data.get('require_ad5x', 0), set_data.get('require_native_screen', 0), is_ad5x, is_native_screen):
                continue

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

            file_data.append('')

    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated SAVE_ZMOD_DATA code')

def add_get_zmod_data(file_data, is_ad5x, is_native_screen, categories, settings):
    indent_level = BASE_INDENT_GET_ZMOD_DATA

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated GET_ZMOD_DATA code')
    file_data.append('')

    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"info\" MSG=\"{cat_data.get("get_zmod_data_text", "")}\"")
        file_data.append('')
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
                
            if not validate_setup(set_data.get("require_ad5x", 0), set_data.get("require_native_screen", 0), is_ad5x, is_native_screen):
                continue

            condition = set_data.get('show_condition', None)
            if condition != None:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {condition} %}}")
                indent_level += 1
            setting_type = set_data.get('type', TYPE_ASSUMPTION)

            if setting_type == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}']|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}']|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{setting_type} %}}")

            valid_options = get_valid_options(set_data, is_ad5x, is_native_screen)
            
            if valid_options['allow_generic']:
                if setting_type != 'string':
                    min_valid_value = valid_options['min_value']
                    max_valid_value = valid_options['max_value']
                    
                    if min_valid_value != None:
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% if z{setting.lower()} < {min_valid_value} %}}")
                        file_data.append(((indent_level + 1) * STANDARD_INDENT) + f"{{% set z{setting.lower()} = {min_valid_value} %}}")
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% endif %}}")
                    if max_valid_value != None:
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% if z{setting.lower()} > {max_valid_value} %}}")
                        file_data.append(((indent_level + 1) * STANDARD_INDENT) + f"{{% set z{setting.lower()} = {max_valid_value} %}}")
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% endif %}}")
            else:
                reset_condition = ''
                quotechar = '"' if setting_type == 'string' else ''
                for valid_option in valid_options['valid_values']:
                    if reset_condition != '':
                        reset_condition += ' and '
                    reset_condition += f"z{setting.lower()} != {quotechar}{valid_option}{quotechar}"
                    
                if reset_condition != '':
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {reset_condition} %}}")
                    indent_level += 1
                    
                    if setting_type == 'string':
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = \"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\" %}}")
                    else:
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = {set_data.get('default', DEFAULT_VALUE_ASSUMPTION)} %}}")
                        
                    indent_level -= 1
                    file_data.append((indent_level * STANDARD_INDENT) + f"{{% endif %}}")

            had_generic = False
            is_first = True
            for text_condition, text in set_data.get('get_zmod_data_text', {}).items():
                if text_condition == '*':
                    had_generic = True
                    if not is_first:
                        file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                else:
                    if setting_type != 'string':
                        condition_ad5x = 1 if 'x' in text_condition else -1 if 'm' in text_condition else 0
                        condition_native_screen = 1 if 'n' in text_condition else -1 if 'g' in text_condition else 0
                        text_condition = re.sub(r'[nxmg]', '', text_condition)
                        if not validate_setup(condition_ad5x, condition_native_screen, is_ad5x, is_native_screen):
                            continue
                    
                    had_regular = True
                    prefix = "" if is_first else "el" # "if" or "elif"

                    if not is_first:
                        indent_level -= 1

                    if setting_type == 'string':
                        condition_string = f"{prefix}if z{setting.lower()} == \"{text_condition}\""
                    else:
                        condition_string = f"{prefix}if z{setting.lower()} == {text_condition}"

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

            file_data.append('')

    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated GET_ZMOD_DATA code')

def add_reset_zmod(file_data, is_ad5x, is_native_screen, categories, settings):
    indent_level = BASE_INDENT_RESET_ZMOD

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated _RESET_ZMOD code')
    file_data.append('')

    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"# {category}")
        for setting, set_data in settings.items():
            if set_data.get('category', '') != category or set_data.get('type', '') == 'special':
                continue
            if set_data.get('exclude_from_reset', False):
                continue
            if not set_data.get('show_in_global', True):
                continue
                
            if not validate_setup(set_data.get('require_ad5x', 0), set_data.get('require_native_screen', 0), is_ad5x, is_native_screen):
                continue

            valid_options = get_valid_options(set_data, is_ad5x, is_native_screen)
            settable_values = valid_options['settable_values']

            if len(settable_values) == 0:
                continue

            setting_type = set_data.get('type', TYPE_ASSUMPTION)
            quotechar = '"' if setting_type == 'string' else ''

            if valid_options['allow_generic']:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables['{setting.lower()}'] %}}")
                if_line = None
                for settable_value in settable_values:
                    if if_line == None:
                        if_line = "{% if"
                    else:
                        if_line += " or"
                    if_line += f" z{setting.lower()} == {quotechar}{settable_value}{quotechar}"

                if_line += " %}"

                file_data.append((indent_level * STANDARD_INDENT) + if_line)
                indent_level += 1

            if setting_type == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"\\\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\\\"\"")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={set_data.get('default', DEFAULT_VALUE_ASSUMPTION)}")

            if valid_options['allow_generic']:
                indent_level -= 1
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            file_data.append('')

    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated _RESET_ZMOD code')


def add_global(file_data, is_ad5x, is_native_screen, categories, settings):
    indent_level = BASE_INDENT_GLOBAL

    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated _GLOBAL code')
    file_data.append('')

    # This one is trickier. We need some extra logic here to skip unused pages, and divide into pages.

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
            if not validate_setup(set_data.get('require_ad5x', 0), set_data.get('require_native_screen', 0), is_ad5x, is_native_screen):
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


    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated _GLOBAL code')
    file_data.append('')
    
def process_file(output_file, is_ad5x, is_native_screen, categories, settings):
    file_data = []

    with open('config-template.cfg', 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('# **'):
                if line.strip() == '# ** SAVE_ZMOD_DATA ** #':
                    add_save_zmod_data(file_data, is_ad5x, is_native_screen, categories, settings)
                if line.strip() == '# ** GET_ZMOD_DATA ** #':
                    add_get_zmod_data(file_data, is_ad5x, is_native_screen, categories, settings)
                if line.strip() == '# ** _RESET_ZMOD ** #':
                    add_reset_zmod(file_data, is_ad5x, is_native_screen, categories, settings)
                if line.strip() == '# ** _GLOBAL ** #':
                    add_global(file_data, is_ad5x, is_native_screen, categories, settings)
            else:
                file_data += [line]

    with open(output_file, 'w', encoding='utf-8') as f:
        for line in file_data:
            f.write(line)
            if not line.endswith('\n'):
                f.write('\n')
    

def main():
    with open('zmod_settings.json', 'r', encoding='utf-8') as f:
        settings_json_data = json.load(f)

    categories = settings_json_data['Categories']
    settings = settings_json_data['Settings']
    
    process_file("../ff5m_config_native.cfg", False, True, categories, settings)
    process_file("../ff5m_config_off.cfg", False, False, categories, settings)
    process_file("../ad5x_config_native.cfg", True, True, categories, settings)
    process_file("../ad5x_config_off.cfg", True, False, categories, settings)

if __name__ == "__main__":
    main()