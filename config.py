from configparser import ConfigParser

def config(filename, section):
    parser = ConfigParser()
    parser.read(filename)

    configs = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            configs[param[0]] = param[1]
    else:
        raise Exception('Section {} not found in {} file.'.format(section, filename))
    
    return configs 