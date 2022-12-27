# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import json
import time
from logging import getLogger
import requests
import yaml
from texttable import Texttable
from cement import ex
from beehive3_cli.core.controller import ARGS
from beehive3_cli.plugins.platform.controllers import ChildPlatformController

logger = getLogger(__name__)


class GraphiteController(ChildPlatformController):
    setup_cmp = False

    class Meta:
        label = 'graphite'
        stacked_on = 'platform'
        stacked_type = 'nested'
        description = "graphite management"
        help = "graphite management"

    def pre_command_run(self):
        super(GraphiteController, self).pre_command_run()

    # get data from graphite
    def getdata_from_graphite(self, ip_address_graphite_f, pod_f, vm_f, metrics_f, function_f, period_f,
                              ask_what_kind_of_question_f):
        ip_address_graphite = ip_address_graphite_f
        pod = pod_f
        vm = vm_f
        metrics = metrics_f
        function = function_f
        period = period_f
        tipodato = 'json'
        ask_what_kind_of_question = ask_what_kind_of_question_f

        grafico = False

        # print('1 ip_address_graphite: ',ip_address_graphite)
        # print('2 pod :',pod)
        # print('3 vm :',vm)
        # print('4 metrics :',metrics)
        # print('5 function :',function)
        # print('6 period :',period)
        # print('7 tipodato :',tipodato)

        # os.system('set http_proxy')
        # sys.exit()

        # string_query = 'http://'+ip_address_graphite+'/render/?target='+pod+'.'+vm+'.'+metrics+'.'+function+'
        # &from'+period+'&format'+tipodato
        if ask_what_kind_of_question_f == 'coarse':
            string_query = 'http://' + ip_address_graphite + '/render?target=' + pod + '.' + vm + '.' + \
                           metrics + '.' + function + '&from=-' + period + '&format=' + tipodato
        elif ask_what_kind_of_question_f == 'highestMax':
            string_query = 'http://' + ip_address_graphite + '/render?target=' + 'highestMax(' + pod + '.' + '*' + \
                           '.' + metrics + '.' + 'percentage' + ',10)' + '&from=-' + period + '&format=' + tipodato
        elif ask_what_kind_of_question_f == 'one':
            string_query = 'http://' + ip_address_graphite + '/render?target=' + pod + '.' + vm + '.' + metrics + \
                           '.' + function + '&from=-' + period + '&format=' + tipodato

        content = requests.get(string_query)

        stringa_get = content.text
        len_stringa = len(stringa_get)
        stringa_get = stringa_get[1:(len_stringa - 1)]
        dict_get = yaml.load(stringa_get)

        target = dict_get['target']
        stringa_datapoints = dict_get['datapoints']

        i = 0
        metrica = []
        array_x = []
        array_y = []

        lenmenouno = (len(stringa_datapoints) - 1)

        while i <= lenmenouno:
            metrica = stringa_datapoints[i]
            metrica_valore = metrica[0]
            metrica_tempo = metrica[1]
            if i == 0:
                inizio_tempo = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metrica_tempo))
                # print('Inizio periodo: ',inizio_tempo)

            if i == lenmenouno:
                fine_tempo = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(metrica_tempo))
                # print('Fine periodo: ',fine_tempo)
            media = 0
            tot_value = 0
            if (metrica[0]) or (metrica[0] == 0):
                array_x.insert(i, metrica_tempo)
                array_y.insert(i, metrica_valore)

            i = i + 1

        if ask_what_kind_of_question_f == 'one':
            if len(array_y) != 0:
                # facciamo la somma di ogni valore
                # print('array_y',array_y)
                k = 0
                for z in range(len(array_y)):
                    # print(array_y[z][0])
                    tot_value += array_y[k]
                    k = k + 1
                    media = tot_value / k
            if media >= 0:
                print(media)
            return

        tab1 = Texttable()

        header = ['Inizio', 'Fine', 'Target']
        tab1.header(header)
        tab1.set_cols_width([30, 30, 55])
        row = [inizio_tempo, fine_tempo, target]
        tab1.add_row(row)
        print(tab1.draw())

        # print as table
        stringa_json = json.loads(stringa_get)
        # print (type(stringa_json))

        # print (json.dumps(stringa_json, indent=2))
        # print ('Valore target: ', stringa_json['target'])
        # print ('Misure: ', stringa_json['datapoints'])

        # print ('Numero valori:',(len(stringa_json['datapoints'])))
        num_val = (len(stringa_json['datapoints']))

        tab2 = Texttable()

        i = 0
        header = ('Value', 'Time')
        tab2.header(header)
        tab2.set_cols_align(['r', 'r'])

        while i < num_val:
            # print(stringa_json['datapoints'][i])
            tab2.add_row(stringa_json['datapoints'][i])
            i = i + 1

        print(tab2.draw())

    @ex(
        help='get vm metrics',
        description='get vm metrics',
        arguments=ARGS([
            (['ip_address_graphite'], {'help': 'ip address graphite', 'action': 'store', 'type': str, 'default': None}),
            (['pod'], {'help': 'pod name', 'action': 'store', 'type': str, 'default': None}),
            (['vm'], {'help': 'vm name', 'action': 'store', 'type': str, 'default': None}),
            (['metrics'], {'help': 'metric', 'action': 'store', 'type': str, 'default': None}),
            (['function'], {'help': 'function', 'action': 'store', 'type': str, 'default': None}),
            (['period'], {'help': 'period', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def vm_metric(self):
        ip_address_graphite_b = self.app.pargs.ip_address_graphite
        pod_b = self.app.pargs.pod
        vm_b = self.app.pargs.vm
        metrics_b = self.app.pargs.metrics
        function_b = self.app.pargs.function
        period_b = self.app.pargs.period
        ask_what_kind_of_question_b = 'coarse'

        self.getdata_from_graphite(ip_address_graphite_b, pod_b, vm_b, metrics_b, function_b, period_b,
                                   ask_what_kind_of_question_b)

    @ex(
        help='get vm highest metrics',
        description='get vm highest metrics',
        arguments=ARGS([
            (['ip_address_graphite'], {'help': 'ip address graphite', 'action': 'store', 'type': str, 'default': None}),
            (['pod'], {'help': 'pod name', 'action': 'store', 'type': str, 'default': None}),
            (['metrics'], {'help': 'metric', 'action': 'store', 'type': str, 'default': None}),
            (['function'], {'help': 'function', 'action': 'store', 'type': str, 'default': None}),
            (['period'], {'help': 'period', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def vm_metric_highest(self):
        ip_address_graphite_b = self.app.pargs.ip_address_graphite
        pod_b = self.app.pargs.pod
        vm_b = '*'
        metrics_b = self.app.pargs.metrics
        function_b = self.app.pargs.function
        period_b = self.app.pargs.period
        ask_what_kind_of_question_b = 'highestMax'

        # getdata_from_graphite('10.138.144.75','podto1.kvm','instance-00000010','disk.0','percentage','-30min')
        self.getdata_from_graphite(ip_address_graphite_b, pod_b, vm_b, metrics_b, function_b, period_b,
                                   ask_what_kind_of_question_b)

    @ex(
        help='get vm one metric',
        description='get vm one metric',
        arguments=ARGS([
            (['ip_address_graphite'], {'help': 'ip address graphite', 'action': 'store', 'type': str, 'default': None}),
            (['pod'], {'help': 'pod name', 'action': 'store', 'type': str, 'default': None}),
            (['vm'], {'help': 'vm name', 'action': 'store', 'type': str, 'default': None}),
            (['metrics'], {'help': 'metric', 'action': 'store', 'type': str, 'default': None}),
            (['function'], {'help': 'function', 'action': 'store', 'type': str, 'default': None}),
            (['period'], {'help': 'period', 'action': 'store', 'type': str, 'default': None}),
        ])
    )
    def vm_metric_one(self):
        ip_address_graphite_b = self.app.pargs.ip_address_graphite
        pod_b = self.app.pargs.pod
        vm_b = self.app.pargs.vm
        metrics_b = self.app.pargs.metrics
        function_b = self.app.pargs.function
        period_b = self.app.pargs.period
        ask_what_kind_of_question_b = 'one'

        # getdata_from_graphite('10.138.144.75','podto1.kvm','instance-00000010','disk.0','percentage','-30min')
        self.getdata_from_graphite(ip_address_graphite_b, pod_b, vm_b, metrics_b, function_b, period_b,
                                   ask_what_kind_of_question_b)
