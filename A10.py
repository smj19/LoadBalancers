import json, requests, socket,pprint
from collections import OrderedDict
from datetime import datetime

#Returns session id
def get_session_id(lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'method' : 'authenticate', 'username' : 'username', 'password' : 'pw', 'format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    session_id_raw = json.loads(response.text)
    return session_id_raw

#This method returns hostname    
def get_hostname(session_id, lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'session_id' : session_id, 'method' : 'system.hostname.get','format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    hostname_raw = json.loads(response.text)
    return hostname_raw

#This methon returns the system information like software,firmware versions
def get_system_info(session_id, lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'session_id' : session_id, 'method' : 'system.information.get' , 'format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    system_info_raw = json.loads(response.text)
    return system_info_raw

#This method returns configuration information for all servers
def get_servers(session_id, lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'session_id' : session_id, 'method' : 'slb.server.getAll','format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    servers_raw = json.loads(response.text)
    return servers_raw

#This method returns configuration information for all service groups(name, port etc)
def get_service_groups(session_id, lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'session_id' : session_id, 'method' : 'slb.service_group.getAll','format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    service_groups_raw = json.loads(response.text)
    return service_groups_raw

#This method returns statitics information for all servers and their ports
def get_fetchAllStats(session_id, lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'session_id' : session_id, 'method' : 'slb.server.fetchAllStatistics','format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    hostname_raw = json.loads(response.text)
    return hostname_raw

#This method returns all virtual server configuration information
def get_virtual_servers(session_id, lb_ipaddress):
    api_url = 'http://' + lb_ipaddress + ':80/services/rest/V2.1/'
    params = {'session_id' : session_id, 'method' : 'slb.virtual_server.getAll','format' : 'json'}
    response = requests.get(api_url, params = params, timeout = 5)
    virtual_servers_raw = json.loads(response.text)
    return virtual_servers_raw

#Returns hostname
def format_hostname(data):
  return data['hostname']

#Returns software, firmware versions and last config saved by looking up the JSON returned by the API
def format_system_info(data):
  return data['system_information']['software_version'], data['system_information']['firmware_version'],data['system_information']['last_config_saved']

#Returns a dictionary of name as key and ip addresses as values for each server
def format_get_server_list(servers_dict):
  server_list = servers_dict["server_list"]
  dict = {}

  for i in range(0,len(server_list)):
      server_name = server_list[i]
      server_name = str(server_name["name"])
      server_ip = server_list[i]
      ip = str(server_ip["host"])
      dict[server_name] = ip
  return dict

#Maps service group names with the corresponding ip addresses
def get_list_server(service_group, server_list_raw):
  server_dict = format_get_server_list(server_list_raw)
  service_group = {server_dict[k]: v for k,v in service_group.items()}
  serv_dict = get_servername(service_group)
  return serv_dict

#Returns server name, port number and the status
def get_list_sg(name_service_group ,service_group,i,server_status_dict):

    service_group_dict = {}
    serviceGroup = service_group[i]
    sg_memberList = serviceGroup["member_list"]
    server_dict = server_status_dict["server_status_list"]
    status_dict = {}
    for i in range(0,len(sg_memberList)):
        value = {}
        port_dict = {}
        sb_memberList_server =  sg_memberList[i]
        server = str(sb_memberList_server["server"])

        sg_memberList_port  =  sg_memberList[i]
        port = str(sg_memberList_port["port"])
        sb_memberList_status =  sg_memberList[i]
        stat = sb_memberList_status["status"]
        #if status is 0, server down. Else if 1, check if it is disabled or under maintanence
        if stat == 0:
          statu = str(stat)
          port_dict["server_status"] = statu
        else:
          value = server_dict.get(server)
          server_status = value.get(port)
          port_dict["server_status"] = server_status

        port_dict["port"] = port
        status_dict[server]=port_dict

    service_group_dict[str(name_service_group)] = status_dict

    return service_group_dict

#get a list of all servers and append it to the corresponding service group dictionary
def format_hostname_dict(hostname_dict,server_status_dict):
    dict = []
    length =  len(hostname_dict['service_group_list'])
    service_group = hostname_dict['service_group_list']
    for i in range(0,length):
        name = service_group[i]
        name_service_group = name["name"]
        dict.append(get_list_sg(name_service_group ,service_group,i,server_status_dict))
    return dict


#Format service groups dict and also checking for subnets if present
def format_service_group(servers_raw, service_groups_raw, virtual_servers_raw,server_status_dict):
  service_group_dict = format_hostname_dict(service_groups_raw,server_status_dict)

  virtual_server_list = virtual_servers_raw["virtual_server_list"]
  length = len(virtual_server_list)
  serv = main_func(service_group_dict, servers_raw)
  #checks for subnet
  list = subnet_check(length,virtual_server_list,serv)
  return list

#return servers sorted based on the hostnames 
def get_servername(server_group):
  for k,v in server_group.items():
    host_dict = {}
    ipaddr = k
    port = v
    another_dict = host_dict
    #return hostnames for each ip address. If DNS lookup fails, return the ip address itself
    try:
      name,b,ip =  socket.gethostbyaddr(ipaddr)
      host_dict["server_hostname"] = name
      host_dict["port"] = port
      host_dict.update(v)
      server_group[k] = host_dict

    except socket.herror:
      host_dict["server_hostname"] = ipaddr
      host_dict.update(v)
      server_group[k] = host_dict
  #sorting servers based on their hostnames
 # return OrderedDict(sorted(server_group.iteritems(), key=lambda t: t[1]['server_hostname']))
  return server_group

#returns a list of server groups with the port numbers
def main_func(service_group_dict, server_list_raw):
    final_servgroup_dict = {}
    for i in range(0,len(service_group_dict)):
        host_dict = {}
        server1_dict = {}
        #grp_dict is the value part
        grp_dict = service_group_dict[i].itervalues().next()
        #name_dict is the key
        name_dict = service_group_dict[i].iterkeys().next()
        #send the values to get_list to get list of ip addresses with port
        server_list = get_list_server(grp_dict, server_list_raw)
        #assigning list of ips with port to each group name in key:value manner
        final_servgroup_dict[name_dict] = server_list

    return final_servgroup_dict
#Checks for subnets, returns a list of service groups with names, corresponding ip addresses, port number, status sorted based on the port numbers
def subnet_check(length, vips_dict0,serv):
  list1 = []
  vport = {}
  for i in range(0,length):
    if "address" in vips_dict0[i]:
      dict1 = {}
      address = vips_dict0[i]
      address =  str(address["address"])
      name = vips_dict0[i]
      name = str(name["name"])
      status = vips_dict0[i]
      status = str(status["status"])
      dict1["name"] = name
      dict1["ip_address"] = address
      dict1["status"] = status
      vport_list = vips_dict0[i]
      #list containing server's ip and ports
      vport_list = vport_list["vport_list"]
      len_port = len(vport_list)
      #for all the server groups, get a dictionary of ports and ip addresses
      vport = get_port(len_port, vport_list,serv)
      #dict1["servers"] = OrderedDict(sorted(vport.items(), key=lambda t: int(t[0])))
      dict1["servers"] = vport
      list1.append(dict1)

    elif "subnet" in vips_dict0[i]:
      dict2 = {}
      sub = vips_dict0[i]
      address =  sub["subnet"]
      address = str(address["address"])
      name = vips_dict0[i]
      name = str(name["name"])
      status = vips_dict0[i]
      status = str(status["status"])
      dict2["name"] = name
      dict2["ip_address"] = address
      dict2["status"] = status
      vport_list = vips_dict0[i]
      #list containing server's ip and ports
      vport_list = vport_list["vport_list"]
      len_port = len(vport_list)
      #for all the server groups, get a dictionary of ports and ip addresses
      vport = get_port(len_port, vport_list,serv)
      dict2["servers"] = OrderedDict(sorted(vport.items(), key=lambda t: int(t[0])))
      list1.append(dict2)

  return list1

#Gets the port of the service group and maps it with the servers behind and their ports
def get_port(length,vport_list,serv):
  port_dict = {}
  vdict = {}
  for i in range(0,length):
    vport_dict = {}
    port = vport_list[i]
    port = str(port["port"])
    service_grp = vport_list[i]
    service_grp = str(service_grp["service_group"])
    vport_dict[port] = service_grp
    vdict = get_list(vport_dict,serv)
    port_dict.update(vdict)
  return port_dict


def get_list(service_list,serv):
    dict = {}
    for k,v in serv.items():
        for key,value in service_list.items():
                if value == k:
                        dict[key] = v
    return dict


#returns a dictionary of port numbers and corresponding status for each server
def get_status(ps):
  d = {}
  for j in range(0,len(ps)):
    port_num =  ps[j]
    port = str(port_num["port_num"])
    st = ps[j]
    status = str(st["status"])
    d[port] = status
  return d

#returns status of a server on each of the corresponding ports
def format_status_info(server_list):
  port_status = {}
  port_list = {}
  final = {}
  list = server_list["server_stat_list"]

  for i in range(0,len(list)):
    server_name = str(list[i]["name"])
    port_stat_list = list[i]["port_stat_list"]
    port_list = get_status(port_stat_list)
    port_status[server_name] = port_list
  final["server_status_list"] = port_status
  return final

#returns final data structure 
def get_final_list_new(lb_ipaddress):
  # Establish session ID.
  system_info = {}
  session_id = get_session_id(lb_ipaddress)['session_id']

  # Query API, save to dictionaries.
  hostname_raw = get_hostname(session_id,lb_ipaddress)
  system_info_raw = get_system_info(session_id,lb_ipaddress)
  servers_raw = get_servers(session_id, lb_ipaddress)
  service_groups_raw = get_service_groups(session_id, lb_ipaddress)
  virtual_servers_raw = get_virtual_servers(session_id,lb_ipaddress)
  server_stat = get_fetchAllStats(session_id,lb_ipaddress)
  server_status_dict = format_status_info(server_stat)

  #formatted information returned
  hostname = format_hostname(hostname_raw)
  software, fw,last_config_saved = format_system_info(system_info_raw)

  str_last = str(last_config_saved)

  newdate = str_last.split()
  del newdate[1]
  newdate = (' ').join(newdate)
  newdate = datetime.strptime(newdate, "%H:%M:%S %a %b %d %Y")
  format_time =  newdate.strftime("%I:%M %p %a %b %d %Y")
  #print format_time
  servers = format_get_server_list(servers_raw)
  service_groups = format_service_group(servers_raw,service_groups_raw,virtual_servers_raw,server_status_dict)
  #Adding information to a dictionary(data structure used)
  system_info["hostname"] = hostname
  system_info["firmware_version"] = str(fw)
  system_info["software_version"] = str(software)
  system_info["last_config_saved"] = str(format_time)
  system_info["service_groups"] = service_groups
  ipaddr = lb_ipaddress
  #return hostname for an ip. If DNS lookup fails, return the ip address itself
  try:
    name,b,ip =  socket.gethostbyaddr(ipaddr)
    system_info["fqdn"] = name
  except socket.herror:
    system_info["fqdn"] = ipaddr


  # Return final data structure.
  return system_info

#pp = pprint.PrettyPrinter(indent=2)
#pp.pprint(get_final_list_new(''))

