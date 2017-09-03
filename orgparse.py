# -*- coding: utf-8 -*-

import json
from pprint import pprint
from Queue import Queue
from PyOrgMode import PyOrgMode
from jinja2 import Template

base = PyOrgMode.OrgDataStructure()
base.load_from_file('./inbox.org')
root = base.root

is_node = lambda x: isinstance(x, PyOrgMode.OrgElement) and 'heading' in x.__dict__

def tree2dict(root, get_nodes):

    ret_todo_list = []

    if hasattr(root, 'todo'):
        ret_todo = dict()
        ret_todo['status'] = root.todo
        ret_todo['heading'] = root.heading
        ret_todo_list.append(ret_todo)

    ret_mindmap = dict()
    ret_mindmap['name'] = root.heading

    # if hasattr(root, 'todo'):
    #     return ret_mindmap

    ret_mindmap['children'] = []

    for node in get_nodes(root):
        (_mdmp, _todo_lsit) = tree2dict(node, get_nodes)
        ret_todo_list = ret_todo_list + _todo_lsit
        ret_mindmap['children'].append(_mdmp)

    if not ret_mindmap['children']:
        del ret_mindmap['children']

    return (ret_mindmap, ret_todo_list)

(mindmap, todo) = tree2dict(root, lambda n: filter(is_node, n.content))

tmpl_f = open('test_bootstrap.html')
tmpl_txt = tmpl_f.read()

tmpl = Template(tmpl_txt.decode('utf-8'))
result = tmpl.render(mindmap_json=('[' + json.dumps(mindmap, ensure_ascii=False) + "]").decode('utf-8'),
                     todo_json=json.dumps(todo, ensure_ascii=False).decode('utf-8'))

out_f = open('out.html', 'w')
out_f.write(result.encode('utf-8'))

tmpl_f.close()
out_f.close()
