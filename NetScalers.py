import requests
import json
import pprint
import socket
from collections import OrderedDict


#api call to get load balancer information
def api_lbinfo(lb_ipaddress):
  api_url = 'http://' + lb_ipaddress + '/nitro/v1/stat/lbvserver/'
  response = requests.get(api_url, auth=('username', 'password'), timeout = 4)
  lb_info = json.loads(response.text)
  #pp.pprint(lb_info)
  return lb_info

#api call to get information about service groups and servers corresponding to each load balancer 
def raw_server_list(lb_ipaddress,grp_name):

  api_url = 'http://' + lb_ipaddress + '/nitro/v1/stat/lbvserver/' + grp_name + '/'
  response = requests.get(api_url, auth=('username', 'password'))
  server_list = json.loads(response.text)
  return server_list


#Returns a list of servers aling with their ip,port,name and status
def get_servers(serv):
  ip_list = {}
  for i in range(0,len(serv)):
    status_dict = {}
    ip_addr = str(serv[i]["primaryipaddress"])
    name = str(serv[i]["name"])
    port = str(serv[i]["primaryport"])
    status = str(serv[i]["state"])
    status_dict['port'] = port
    status_dict['server_hostname'] = name
    if status == "UP":
      status = 1
    else:
      status = 0

    status_dict['server_status'] = str(status)

    ip_list[ip_addr] = status_dict
  return OrderedDict(sorted(ip_list.iteritems(), key=lambda t: t[1]['server_hostname']))


#returns service groups information and servers. Returns empty dict when no servers for a particular group
def get_server_list(raw_servers):
  #pp.pprint(raw_servers)
  for i in range(0,len(raw_servers)):
    port_dict = {}
    service_group = {}
    service = []
    group_name = str(raw_servers[i]["name"])
    service_group["name"] =  group_name
    service_group["ip_address"] = str(raw_servers[i]["primaryipaddress"])
    health = str(raw_servers[i]["vslbhealth"])
    if health > 0:
      health = 1
    else:
      health = 0
    service_group["status"] = str(health)

    port = str(raw_servers[i]["primaryport"])
    if "service" in raw_servers[i]:
      service = raw_servers[i]["service"]
      servers = get_servers(service)
      port_dict[port] = servers
      service_group["servers"] = OrderedDict(sorted(port_dict.items(), key=lambda t: int(t[0])))
    else:
      service_group["servers"] = {}
  return service_group


#returns a list of service groups
def get_servicegroups(ip,lb_info):
  list = []
  lbserv = lb_info["lbvserver"]

  for i in range(0,len(lbserv)):
    service_grp_name = str(lbserv[i]["name"])
    state = str(lbserv[i]["state"])
    raw_servers = raw_server_list(ip,service_grp_name)
    server_list = get_server_list(raw_servers["lbvserver"])
    list.append(server_list)
  return list

#return the final data structure
def get_final_list(lb_ipaddress):

  final_dict = {}
  lb_info = api_lbinfo(lb_ipaddress)
  service_groups = get_servicegroups(lb_ipaddress,lb_info)
  try:
    name,b,ip =  socket.gethostbyaddr(lb_ipaddress)
    final_dict["fqdn"] = name
  except socket.herror:
    final_dict["fqdn"] = lb_ipaddress
  final_dict["service_groups"] = service_groups
  return final_dict

#pp = pprint.PrettyPrinter(indent=2)
#pp.pprint(get_final_list('10.85.2.22'))

