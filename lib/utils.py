import socket, json

def isIP(ip):
    try:
        socket.inet_aton(ip)
        return True
    except:
        return False

def replaceURLencoded(data, match, newValue):
    if not data:
        return None
    new_data = ''
    for p in data.split('&'):
        if len(p.split('=')) == 1:
            return None
        elif match is None or match.lower() in p.split('=')[0].lower():
            new_data += p.split('=')[0]
            new_data += '=' + newValue + '&'
        else:
            new_data += p + '&'
    return new_data[:-1]

def replaceJSON(data, match, newValue):
    for k,v in data.items():
        if isinstance(v, dict):
            data.update({k:replaceJSON(v, match, newValue)})
        else:
            if match is None or match.lower() in k.lower():
                data.update({k:newValue})
    return data

# Substitutes all values whose keys match with match parameter to newValue. If match is None, it will substitute all values.
# It uses content_type header to know what type of POST data is, so it can be more precise
# For multipart/form-data, it also substitutes the boundary since its value is usually random/partially random
# If an exception occurs, a copy of the original data is returned
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Type

def substitutePOSTData(content_type, data, match, newValue):
    boundary_substitute = 'BOUNDARY'

    if not data:
        return None
    
    if not content_type:
        try:
            return json.dumps(replaceJSON(json.loads(data), match, newValue))
        except:
            return  replaceURLencoded(data, match, newValue)

    try:
        if 'multipart/form-data' in content_type:
            # If data has already been parsed so boundary has changed
            if '--'+boundary_substitute in data:
                boundary = '--'+boundary_substitute
            else:
                boundary = '--' + content_type.split('; ')[1].split('=')[1]

            new_data = '--'+boundary_substitute
            for fragment in data.split(boundary)[1:-1]:
                name = fragment.split('\r\n')[1].split('; ')[1].split('=')[1].strip('"')
                content = fragment.split('\r\n')[3]

                try:
                    new_content = json.dumps(replaceJSON(json.loads(content), match, newValue))
                except:
                    new_content = replaceURLencoded(content, match, newValue)
                
                if not new_content:
                    if match.lower() in name.lower() or match is None:
                        new_content = newValue
                    else:
                        new_content = content
                
                new_data += fragment.split('name="')[0] + 'name="' + name + '"; ' + "; ".join(fragment.split('\r\n')[1].split('; ')[2:]) + '\r\n\r\n' + new_content + '\r\n--'+boundary_substitute
            new_data += '--'

            return new_data
        elif 'application/json' in content_type:
            return json.dumps(replaceJSON(json.loads(data), match, newValue))
        elif 'application/x-www-form-urlencoded' in content_type:
            return replaceURLencoded(data, match, newValue)
    except Exception as e:
        print('[x] Exception %s ocurred when parsing POST data' % (e.__class__.__name__))
    finally:
        return data