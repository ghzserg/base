import json
import re

STANDARD_INDENT = '    '
BASE_INDENT_SAVE_ZMOD_DATA = 1
BASE_INDENT_GET_ZMOD_DATA = 1
BASE_INDENT_RESET_ZMOD = 1
BASE_INDENT_GLOBAL = 1

ITEMS_PER_GLOBAL_PAGE = 4

DEFAULT_VALUE_ASSUMPTION = 0
DEFAULT_STRING_ASSUMPTION = ""
TYPE_ASSUMPTION = 'int'

def add_save_zmod_data(file_data, categories, settings):
    indent_level = BASE_INDENT_SAVE_ZMOD_DATA
    
    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated SAVE_ZMOD_DATA code')
    file_data.append(indent_level * STANDARD_INDENT)
    
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
                                
            file_data.append(indent_level * STANDARD_INDENT)
            
    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated SAVE_ZMOD_DATA code')
    
def add_get_zmod_data(file_data, categories, settings):
    indent_level = BASE_INDENT_GET_ZMOD_DATA
    
    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated GET_ZMOD_DATA code')
    file_data.append(indent_level * STANDARD_INDENT)
    
    for category, cat_data in categories.items():
        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND PREFIX=\"info\" MSG=\"{cat_data.get("get_zmod_data_text", "")}\"")
        file_data.append(indent_level * STANDARD_INDENT)
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
            
            condition = set_data.get('condition', None)
            if condition != None:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {condition} %}}")
                indent_level += 1
            setting_type = set_data.get('type', TYPE_ASSUMPTION)
            
            if setting_type == 'string':
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables.{setting.lower()}|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
            else:
                file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables.{setting.lower()}|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{setting_type} %}}")
                
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
            
            file_data.append(indent_level * STANDARD_INDENT)                
    
    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated GET_ZMOD_DATA code')

def add_reset_zmod(file_data, categories, settings):
    indent_level = BASE_INDENT_RESET_ZMOD
    
    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated _RESET_ZMOD code')
    file_data.append(indent_level * STANDARD_INDENT)        
    
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
            
            if set_data.get('type', TYPE_ASSUMPTION) == 'string':
                target.append(((indent_level + extra_indent) * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE=\"\\\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\\\"s\"")
            else:
                target.append(((indent_level + extra_indent) * STANDARD_INDENT) + f"SAVE_VARIABLE VARIABLE={setting.lower()} VALUE={set_data.get('default', DEFAULT_VALUE_ASSUMPTION)}")
        
        file_data += both_entries
        
        if len(ad5m_entries) > 0:
            file_data.append((indent_level * STANDARD_INDENT) + "{% if not client.ad5x %}")
            file_data += ad5m_entries
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            
        if len(ad5x_entries) > 0:
            file_data.append((indent_level * STANDARD_INDENT) + "{% if client.ad5x %}")
            file_data += ad5x_entries
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            
        file_data.append(indent_level * STANDARD_INDENT)        
    
    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated _RESET_ZMOD code')
            
    
def add_global(file_data, categories, settings):
    indent_level = BASE_INDENT_GLOBAL
    
    file_data.append((indent_level * STANDARD_INDENT) + '# Begin script-generated _GLOBAL code')
    file_data.append(indent_level * STANDARD_INDENT)      
    
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
                setting_entries += [{"header": cat_data.get("global_text", ""), "settings": category_entries}]
                
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
                        file_data.append((indent_level - 1) * STANDARD_INDENT)
                        
                        page += 1
                        items_on_page = 0
                    if items_on_page == 0:
                        file_data.append(((indent_level - 1) * STANDARD_INDENT) + f"{{% if n == {page} and start == 0 %}}")
                        file_data.append((indent_level * STANDARD_INDENT) + f"{{% set this_page_visible_items = 0 %}}")
                        file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_begin Page {page} : {category_entry['header']}\"")
                        file_data.append(indent_level * STANDARD_INDENT)
                    
                    # Add item here
                    setting_type = set_data.get('type', TYPE_ASSUMPTION)
                    
                    if setting_type == "special":
                        code = set_data.get('code', '').replace('\r', '').split('\n')
                        file_data.append((indent_level * STANDARD_INDENT) + "{% set this_page_visible_items = this_page_visible_items + 1 %}")
                        for line in code:
                            file_data.append((indent_level * STANDARD_INDENT) + line)
                        file_data.append(indent_level * STANDARD_INDENT)
                        items_on_page += 1
                    else:                    
                        condition = set_data.get('condition', None)
                        if condition != None:
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if {condition} %}}")
                            indent_level += 1

                        if setting_type == 'string':
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables.{setting.lower()}|default(\"{set_data.get('default', DEFAULT_STRING_ASSUMPTION)}\")|string %}}")
                        else:
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% set z{setting.lower()} = printer.save_variables.variables.{setting.lower()}|default({set_data.get('default', DEFAULT_VALUE_ASSUMPTION)})|{setting_type} %}}")

                        texts = set_data.get('global_text', None)
                        if texts == None:
                            texts = set_data.get('get_zmod_data_text', {})

                        set_values = set_data.get('global_set_values', None)
                        if set_values == None:
                            set_values = []
                            for text_condition in texts.keys():
                                if setting_type != 'string':
                                    text_condition = re.sub(r'[nx]', '', text_condition)
                                if text_condition == '*':
                                    break
                                if text_condition not in set_values:
                                    set_values += [text_condition]

                        complete = []
                        had_generic = False
                        is_first = True
                        for text_condition, text in texts.items():
                            if text_condition == '*':
                                had_generic = True
                                if not is_first:
                                    file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                            else:
                                prefix = "" if is_first else "el" # "if" or "elif"

                                if setting_type != 'string':
                                    if 'n' in text_condition and not is_native_screen:
                                        continue
                                    if 'x' in text_condition and not is_ad5x:
                                        continue
                                    text_condition = re.sub(r'[nx]', '', text_condition)

                                if text_condition in complete:
                                    continue

                                complete += [text_condition]

                                condition_string = f"{prefix}if z{setting.lower()} == "

                                if setting_type == 'string':
                                    condition_string += f"\"{text_condition}\""
                                else:
                                    condition_string += f"{text_condition}"

                                had_regular = True

                                if not is_first:
                                    indent_level -= 1
                                file_data.append((indent_level * STANDARD_INDENT) + f"{{% {condition_string} %}}")    
                                indent_level += 1

                            if len(set_values) > 0:
                                try:
                                    next_value_index = set_values.index(text_condition) + 1
                                    if next_value_index >= len(set_values):
                                        next_value_index = 0
                                except ValueError:
                                    next_value_index = 0

                                next_value = set_values[next_value_index]
                            else:
                                next_value = None

                            if next_value == None:
                                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {text}|_GLOBAL N={page}|primary\"")
                            else:
                                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {text}|SAVE_ZMOD_DATA {setting.upper()}={next_value} I={page}|primary\"")

                            if had_generic:
                                break

                            is_first = False

                        if not had_generic:
                            if not is_first:
                                file_data.append(((indent_level - 1) * STANDARD_INDENT) + "{% else %}")
                            if len(set_values) == 0:
                                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {setting.upper()} ===unknown value:=== {{z{setting.lower()}}}|_GLOBAL N={page}|primary\"")
                            else:
                                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_button {setting.upper()} ===unknown value:=== {{z{setting.lower()}}}|SAVE_ZMOD_DATA {setting.upper()}={set_values[0]} I={page}|primary\"")

                        if not is_first or not had_generic:
                            indent_level -= 1
                            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                            
                        file_data.append((indent_level * STANDARD_INDENT) + "{% set this_page_visible_items = this_page_visible_items + 1 %}")

                        if condition != None:
                            indent_level -= 1
                            file_data.append((indent_level * STANDARD_INDENT) + f"{{% endif %}}")

                        file_data.append(indent_level * STANDARD_INDENT)
                        items_on_page += 1
                    
                if items_on_page > 0:
                    items_on_page = ITEMS_PER_GLOBAL_PAGE # force page change between categories
                                         
            if items_on_page > 0:
                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_footer_button ===Next===|_GLOBAL N={page + 1}|red\"")
                file_data.append((indent_level * STANDARD_INDENT) + f"RESPOND TYPE=command MSG=\"action:prompt_show\"")
                indent_level -= 1                         
                file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")  
                file_data.append(indent_level * STANDARD_INDENT)              
                page += 1
                
            file_data.append((indent_level * STANDARD_INDENT) + f"{{% if n >= {page} and start == 0 %}}")
            file_data.append(((indent_level + 1) * STANDARD_INDENT) + "_SHOW_MSG MSG=\"===If any parameters were changed, it is recommended to reboot the printer===. Macro GLOBAL\" COMMAND='_GLOBAL_SAVE PARAM=skip_global' COMMAND_REBOOT=\"_GLOBAL_SAVE PARAM=skip_global REBOOT=1\"")
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
            # _SHOW_MSG MSG=\"===If any parameters were changed, it is recommended to reboot the printer===. Macro GLOBAL\" COMMAND='_GLOBAL_SAVE PARAM=skip_global' COMMAND_REBOOT=\"_GLOBAL_SAVE PARAM=skip_global REBOOT=1\"
            
            indent_level -= 1
            file_data.append((indent_level * STANDARD_INDENT) + "{% endif %}")
                             
    
    file_data.append((indent_level * STANDARD_INDENT) + '# End script-generated _GLOBAL code')
    file_data.append(indent_level * STANDARD_INDENT)

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