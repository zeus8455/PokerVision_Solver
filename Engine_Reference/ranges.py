from __future__ import annotations

"""Separated preflop range data for 6-max NLHE cash.

This module contains only editable chart/range dictionaries and the assembled
hero/opponent profiles. Logic for parsing, validation and action selection lives
in preflop_advisor.py.
"""

from typing import Dict, Tuple

# -----------------------------------------------------------------------------
# Shared / base charts
# -----------------------------------------------------------------------------

RFI_RAISE = {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
 'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
 'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
 'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ T9o+'}

OPEN_LIMP = {'MP': '22+ A2s+ K8s+ Q8s+ J8s+ T8s+ 97s+ 86s+ 76s A2o+ KTo+ QTo+ JTo T9o',
 'CO': '22+ A2s+ K7s+ Q8s+ J8s+ T7s+ 97s+ 86s+ 75s+ 65s A2o+ KTo+ QTo+ JTo T9o',
 'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 74s+ 65s+ A2o+ K8o+ Q9o+ J9o+ T8o+'}

SB_FIRST_IN = {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
 'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s 53s 43s A2o+ K2o-KJo Q8o-QJo '
         'J8o-JTo T8o 98o'}

ISO_RAISE = {'UTG': {},
 'MP': '88+ AJs+ KQs AQo+',
 'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
 'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
 'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
 'BB': '88+ AJs+ KQs AQo+'}

OVER_LIMP = {'MP': '22-99 A2s-ATs KTs QTs JTs T9s 98s',
 'CO': '22-99 A2s-ATs K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A8o-ATo KTo QTo',
 'BTN': '22-88 A2s-ATs K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s A7o-ATo KTo-KJo QTo',
 'SB': '22-99 A2s-AJs K9s-KJs Q8s-QJs JTs T9s 98s 87s 76s A2o-ATo KTo-KQo QTo-QJo JTo'}

BB_VS_SB_LIMP = {'raise': '22+ A2s+ K5s+ Q8s+ J7s+ T7s+ 96s+ 86s+ 76s 65s A8o+ KTo+ QTo+ JTo',
 'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s J2s-J7s T2s-T7s 92s-96s '
          '82s-86s 72s-75s 62s-64s 52s-54s 42s-43s 32s'}

VS_OPEN: Dict[Tuple[str, str], Dict[str, str]] = {('UTG', 'MP'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                 'call': '55-TT A8s-AQs KJs-KQs QJs JTs T9s 98s 87s AJo-AQo KQo'},
 ('UTG', 'CO'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                 'call': '44-TT A7s-AQs KTs-KQs QJs JTs T9s 98s 87s AJo-AQo KJo-KQo'},
 ('UTG', 'BTN'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                  'call': '22-TT A6s-AQs KTs-KQs QTs-QJs JTs T9s 98s 87s 76s AJo-AQo KJo-KQo'},
 ('UTG', 'SB'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                 'call': '22-TT A4s-AQs K9s-KQs QTs-QJs JTs T9s 98s 87s 76s ATo-AQo KJo-KQo QJo'},
 ('UTG', 'BB'): {'3bet': 'JJ+ AJs+ KQs AJo+ KQo',
                 'call': '22-JJ A2s-AQs K2s-KQs Q2s-QJs J5s-JTs T5s-T9s 95s+ 85s+ 74s+ 64s+ 54s 43s A2o-AQo '
                         'K8o-KQo Q8o+ J8o+ T8o+ 98o'},
 ('MP', 'CO'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                'call': '44-TT A7s-AQs KJs-KQs QJs JTs T9s 98s 87s AJo-AQo KJo-KQo QJo'},
 ('MP', 'BTN'): {'3bet': 'TT+ AJs+ KJs-KQs AJo+ KJo-KQo',
                 'call': '22-TT A5s-AQs KTs-KQs QTs-QJs JTs T9s 98s 87s ATo-AQo KJo-KQo QJo'},
 ('MP', 'SB'): {'3bet': '99+ ATs+ KJs-KQs AJo+ KJo-KQo',
                'call': '22-TT A2s-AQs KTs-KQs QTs-QJs JTs T9s 98s 87s ATo-AQo KJo-KQo QJo'},
 ('MP', 'BB'): {'3bet': '99+ ATs+ KJs-KQs AJo+ KJo-KQo',
                'call': '22-TT A2s-AQs K2s-KQs Q2s-QJs J5s-JTs T5s-T9s 95s+ 85s+ 74s+ 64s+ 54s 43s A2o-AQo '
                        'K8o-KQo Q8o+ J8o+ T8o+ 98o'},
 ('CO', 'BTN'): {'3bet': '88+ ATs+ KJs+ ATo+ KJo+',
                 'call': '22-TT A2s-AQs KTs-KQs QJs JTs T9s 98s 87s ATo-AQo KJo-KQo QJo'},
 ('CO', 'SB'): {'3bet': '88+ ATs+ KJs+ ATo+ KJo+',
                'call': '22-TT A2s-AQs KTs-KQs QJs JTs T9s 98s 87s ATo-AQo KJo-KQo QJo'},
 ('CO', 'BB'): {'3bet': 'TT+ ATs+ KQs ATo+ KQo',
                'call': '22-TT A2s-AQs K2s-KQs Q2s-QJs J5s-JTs T5s-T9s 95s+ 85s+ 74s+ 64s+ 54s 43s A2o-AQo '
                        'K8o-KQo Q7o+ J7o+ T8o+ 98o 87o'},
 ('BTN', 'SB'): {'3bet': '88+ A9s+ KJs+ ATo+ KJo+',
                 'call': '22-TT A2s-AQs KTs-KQs QJs JTs T9s 98s 87s ATo-AQo KJo-KQo QJo'},
 ('BTN', 'BB'): {'3bet': 'TT+ ATs+ KQs ATo+ KQo',
                 'call': '22-TT A2s-AQs K2s-KQs Q2s-QJs J5s-JTs T5s-T9s 95s+ 85s+ 74s+ 64s+ 54s 43s A2o-AQo '
                         'K8o-KQo Q7o+ J7o+ T8o+ 98o 87o'},
 ('SB', 'BB'): {'3bet': 'TT+ AJs+ AJo+ A2s-A5s KJs-KQs QJs JTs T9s 98s',
                'call': '22-TT A2s-AJs K2s+ Q5s+ J7s+ T7s+ 97s+ 86s+ 75s+ 64s+ 54s A2o-AJo K8o-KQo Q9o+ J9o+ '
                        'T8o+ 98o'}}

VS_OPEN_CALLERS: Dict[Tuple[str, str, int], Dict[str, str]] = {('UTG', 'CO', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-JJ A8s-AQs KJs+ QJs JTs T9s 98s 87s AJo KJo+ QJo'},
 ('UTG', 'BTN', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                     'call': '22-JJ A6s-AQs KTs+ QTs+ JTs T9s 98s 87s AJo KJo+ QJo'},
 ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-JJ A6s-AQs KTs+ QTs+ JTs T9s 98s 87s AJo KJo+ QJo'},
 ('UTG', 'BB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-TT A2s-AJs K2s+ Q5s+ J7s+ T7s+ 97s+ 86s+ 75s+ 64s+ 54s A2o-AJo K8o-KQo Q9o+ '
                            'J9o+ T8o+ 98o'},
 ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-JJ A8s-AQs KJs+ QJs JTs T9s 98s 87s AJo KJo+ QJo'},
 ('MP', 'SB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                   'call': '22-JJ A8s-AQs KJs+ QJs JTs T9s 98s 87s AJo KJo+ QJo'},
 ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                   'call': '22-TT A2s-AJs K2s+ Q5s+ J7s+ T7s+ 97s+ 86s+ 75s+ 64s+ 54s A2o-AJo K8o-KQo Q9o+ '
                           'J9o+ T8o+ 98o'},
 ('CO', 'BTN', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-JJ A8s-AQs KJs+ QJs JTs T9s 98s 87s AJo KJo+ QJo'},
 ('CO', 'SB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                   'call': '22-JJ A8s-AQs KJs+ QJs JTs T9s 98s 87s AJo KJo+ QJo'},
 ('CO', 'BB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                   'call': '22-TT A2s-AJs K2s+ Q5s+ J7s+ T7s+ 97s+ 86s+ 75s+ 64s+ 54s A2o-AJo K8o-KQo Q9o+ '
                           'J9o+ T8o+ 98o'},
 ('BTN', 'BB', 1): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-TT A2s-AJs K2s+ Q5s+ J7s+ T7s+ 97s+ 86s+ 75s+ 64s+ 54s A2o-AJo K8o-KQo Q9o+ '
                            'J9o+ T8o+ 98o'},
 ('CO', 'BB', 2): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                   'call': '22-JJ A2s-AQs KTs+ Q9s+ J8s+ T7s+ 97s+ 86s+ 76s ATo-AQo KTo+ QTo+ JTo'},
 ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ KQs AQo+ KQo',
                    'call': '22-JJ A2s-AQs KTs+ Q9s+ J8s+ T7s+ 97s+ 86s+ 76s ATo-AQo KTo+ QTo+ JTo'}}

OPENER_VS_3BET: Dict[Tuple[str, str], Dict[str, str]] = {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
 ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
 ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
 ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
 ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
 ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
 ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
 ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
 ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
 ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
 ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs'},
 ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
 ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
 ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
 ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s', 'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}}

THREEBETTER_VS_4BET: Dict[Tuple[str, str], Dict[str, str]] = {('MP', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('CO', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BTN', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('CO', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BTN', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('SB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'}}

COLD_4BET: Dict[Tuple[str, str, str], Dict[str, str]] = {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
 ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}

# -----------------------------------------------------------------------------
# Hero charts
# -----------------------------------------------------------------------------

HERO_RFI_RAISE = {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
 'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
 'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
 'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ T9o+'}

HERO_SB_FIRST_IN = {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
 'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s 53s 43s A2o+ K2o-KJo Q8o-QJo '
         'J8o-JTo T8o 98o'}

HERO_ISO_RAISE = {'UTG': {},
 'MP': '88+ AJs+ KQs AQo+',
 'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
 'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
 'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
 'BB': '88+ AJs+ KQs AQo+'}

HERO_OVER_LIMP = {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
 'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
 'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s A8o-ATo KTo-KJo QTo',
 'SB': '22-55 A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'}

HERO_OPEN_LIMP = {}

HERO_BB_VS_SB_LIMP = {'raise': '22+ A2s+ K5s+ Q8s+ J8s+ T8s+ 97s+ 87s 76s 65s A8o+ KTo+ QTo+ JTo',
 'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s J2s-J7s T2s-T7s 92s-96s '
          '82s-86s 72s-75s 62s-64s 52s-54s 42s-43s 32s'}

HERO_VS_OPEN: Dict[Tuple[str, str], Dict[str, str]] = {('UTG', 'MP'): {'3bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs QJs JTs T9s 98s'},
 ('UTG', 'CO'): {'3bet': 'QQ+ AKs AKo A5s', 'call': '88-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
 ('UTG', 'BTN'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                  'call': '77-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
 ('UTG', 'SB'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs', 'call': '99-TT AJs-AQs KQs QJs JTs T9s'},
 ('UTG', 'BB'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                 'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s ATo-AQo KJo-KQo '
                         'QJo'},
 ('MP', 'CO'): {'3bet': 'JJ+ AQs+ AKo A5s', 'call': '77-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AQo KQo'},
 ('MP', 'BTN'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                 'call': '55-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
 ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs', 'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
 ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s A9o-AQo KTo-KQo '
                        'QJo JTo'},
 ('CO', 'BTN'): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                 'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s ATo-AQo KJo-KQo QJo'},
 ('CO', 'SB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs QJs', 'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
 ('CO', 'BB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs JTs',
                'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s 98s A8o-AJo K9o-KQo '
                        'Q9o-QJo JTo'},
 ('BTN', 'SB'): {'3bet': '99+ ATs+ AJo+ A2s-A5s K9s-KQs QTs+ JTs T9s',
                 'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s 98s ATo KTo-KQo QTo+ '
                         'JTo'},
 ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                 'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s A2o-ATo '
                         'K8o-KQo QTo+ JTo'},
 ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s A2o-ATo '
                        'K8o-KQo QTo+ JTo'}}

HERO_VS_OPEN_CALLERS: Dict[Tuple[str, str, int], Dict[str, str]] = {('UTG', 'CO', 1): {'3bet': 'QQ+ AKs AKo A5s', 'call': '99-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
 ('UTG', 'BTN', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                     'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s AQo'},
 ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s', 'call': '99-TT AJs-AQs KQs QJs JTs'},
 ('UTG', 'BB', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                    'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s ATo-AQo '
                            'KJo-KQo'},
 ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                    'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s AQo KQo'},
 ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ AKo A5s-A4s', 'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
 ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A2s-A5s',
                   'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s A9o-AQo '
                           'KTo-KQo QJo'},
 ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                    'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s ATo-AQo KJo-KQo'},
 ('CO', 'SB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs', 'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s'},
 ('CO', 'BB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs',
                   'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s 98s A8o-AJo '
                           'K9o-KQo Q9o-QJo'},
 ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                    'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s 64s 75s 86s 97s 98s A2o-ATo '
                            'K9o-KQo QTo+ JTo'},
 ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s', 'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
 ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s', 'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}}

HERO_OPENER_VS_3BET: Dict[Tuple[str, str], Dict[str, str]] = {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
 ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
 ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
 ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
 ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
 ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
 ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
 ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
 ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
 ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
 ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs'},
 ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
 ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
 ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
 ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s', 'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}}

HERO_THREEBETTER_VS_4BET: Dict[Tuple[str, str], Dict[str, str]] = {('MP', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('CO', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BTN', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('CO', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BTN', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('SB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'}}

HERO_COLD_4BET: Dict[Tuple[str, str, str], Dict[str, str]] = {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
 ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}

# -----------------------------------------------------------------------------
# Opponent charts
# -----------------------------------------------------------------------------

OPPONENT_RFI_RAISE = {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
 'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
 'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
 'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ T9o+'}

OPPONENT_SB_FIRST_IN = {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
 'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s 53s 43s A2o+ K2o-KJo Q8o-QJo '
         'J8o-JTo T8o 98o'}

OPPONENT_ISO_RAISE = {'UTG': {},
 'MP': '88+ AJs+ KQs AQo+',
 'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
 'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
 'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
 'BB': '88+ AJs+ KQs AQo+'}

OPPONENT_OVER_LIMP = {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
 'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
 'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s A8o-ATo KTo-KJo QTo',
 'SB': '22-55 A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'}

OPPONENT_OPEN_LIMP = {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
 'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
 'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s A8o-ATo KTo-KJo QTo'}

OPPONENT_BB_VS_SB_LIMP = {'raise': '22+ A2s+ K5s+ Q8s+ J8s+ T8s+ 97s+ 87s 76s 65s A8o+ KTo+ QTo+ JTo',
 'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s J2s-J7s T2s-T7s 92s-96s '
          '82s-86s 72s-75s 62s-64s 52s-54s 42s-43s 32s'}

OPPONENT_VS_OPEN: Dict[Tuple[str, str], Dict[str, str]] = {('UTG', 'MP'): {'3bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs QJs JTs T9s 98s'},
 ('UTG', 'CO'): {'3bet': 'QQ+ AKs AKo A5s', 'call': '88-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
 ('UTG', 'BTN'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                  'call': '77-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
 ('UTG', 'SB'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs', 'call': '99-TT AJs-AQs KQs QJs JTs T9s'},
 ('UTG', 'BB'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                 'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s ATo-AQo KJo-KQo '
                         'QJo'},
 ('MP', 'CO'): {'3bet': 'JJ+ AQs+ AKo A5s', 'call': '77-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AQo KQo'},
 ('MP', 'BTN'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                 'call': '55-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
 ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs', 'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
 ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s A9o-AQo KTo-KQo '
                        'QJo JTo'},
 ('CO', 'BTN'): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                 'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s ATo-AQo KJo-KQo QJo'},
 ('CO', 'SB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs QJs', 'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
 ('CO', 'BB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs JTs',
                'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s 98s A8o-AJo K9o-KQo '
                        'Q9o-QJo JTo'},
 ('BTN', 'SB'): {'3bet': '99+ ATs+ AJo+ A2s-A5s K9s-KQs QTs+ JTs T9s',
                 'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s 98s ATo KTo-KQo QTo+ '
                         'JTo'},
 ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                 'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s A2o-ATo '
                         'K8o-KQo QTo+ JTo'},
 ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s A2o-ATo '
                        'K8o-KQo QTo+ JTo'}}

OPPONENT_VS_OPEN_CALLERS: Dict[Tuple[str, str, int], Dict[str, str]] = {('UTG', 'CO', 1): {'3bet': 'QQ+ AKs AKo A5s', 'call': '99-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
 ('UTG', 'BTN', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                     'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s AQo'},
 ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s', 'call': '99-TT AJs-AQs KQs QJs JTs'},
 ('UTG', 'BB', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                    'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s ATo-AQo '
                            'KJo-KQo'},
 ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                    'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s AQo KQo'},
 ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ AKo A5s-A4s', 'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
 ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A2s-A5s',
                   'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s A9o-AQo '
                           'KTo-KQo QJo'},
 ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                    'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s ATo-AQo KJo-KQo'},
 ('CO', 'SB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs', 'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s'},
 ('CO', 'BB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs',
                   'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s 98s A8o-AJo '
                           'K9o-KQo Q9o-QJo'},
 ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                    'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s 64s 75s 86s 97s 98s A2o-ATo '
                            'K9o-KQo QTo+ JTo'},
 ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s', 'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
 ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s', 'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}}

OPPONENT_OPENER_VS_3BET: Dict[Tuple[str, str], Dict[str, str]] = {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
 ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
 ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
 ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
 ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
 ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
 ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
 ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
 ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
 ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
 ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs'},
 ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
 ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
 ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
 ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s', 'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}}

OPPONENT_THREEBETTER_VS_4BET: Dict[Tuple[str, str], Dict[str, str]] = {('MP', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('CO', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BTN', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('CO', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BTN', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('SB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('BB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
 ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
 ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'}}

OPPONENT_COLD_4BET: Dict[Tuple[str, str, str], Dict[str, str]] = {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
 ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
 ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}

# -----------------------------------------------------------------------------
# Profile assembly
# -----------------------------------------------------------------------------

def _build_chart_profile(
    *,
    rfi_raise: Dict[str, str],
    sb_first_in: Dict[str, str],
    iso_raise: Dict[str, str],
    over_limp: Dict[str, str],
    open_limp: Dict[str, str],
    bb_vs_sb_limp: Dict[str, str],
    vs_open: Dict[Tuple[str, str], Dict[str, str]],
    vs_open_callers: Dict[Tuple[str, str, int], Dict[str, str]],
    opener_vs_3bet: Dict[Tuple[str, str], Dict[str, str]],
    threebettor_vs_4bet: Dict[Tuple[str, str], Dict[str, str]],
    cold_4bet: Dict[Tuple[str, str, str], Dict[str, str]],
) -> Dict[str, object]:
    return {
        "RFI_RAISE": rfi_raise,
        "SB_FIRST_IN": sb_first_in,
        "ISO_RAISE": iso_raise,
        "OVER_LIMP": over_limp,
        "OPEN_LIMP": open_limp,
        "BB_VS_SB_LIMP": bb_vs_sb_limp,
        "VS_OPEN": vs_open,
        "VS_OPEN_CALLERS": vs_open_callers,
        "OPENER_VS_3BET": opener_vs_3bet,
        "THREEBETTER_VS_4BET": threebettor_vs_4bet,
        "COLD_4BET": cold_4bet,
    }


HERO_PREFLOP_CHARTS = {'RFI_RAISE': {'UTG': '55+ A5s+ KTs+ QTs+ JTs+ T9s+ 98s+ ATo+ KJo+ QJo+',
               'MP': '22+ A2s+ K9s+ Q9s+ J9s+ T8s+ 97s+ A9o+ KTo+ QTo+',
               'CO': '22+ A2s+ K8s+ Q7s+ J8s+ T8s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
               'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ T9o+'},
 'SB_FIRST_IN': {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
                 'limp': '22-88 A2s-A7s K2s-KTs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s 53s 43s A2o+ '
                         'K2o-KJo Q8o-QJo J8o-JTo T8o 98o'},
 'ISO_RAISE': {'UTG': {},
               'MP': '88+ AJs+ KJs AJo+ KQo',
               'CO': '77+ ATs+ KTs+ QJs JTs AJo+ KJo',
               'BTN': '66+ A8s+ K9s+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
               'SB': 'TT+ ATs+ KQs+ QJs+ JTs AJo+ KQo',
               'BB': 'TT+ AJs+ KQs AQo+'},
 'OVER_LIMP': {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
               'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
               'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s A8o-ATo KTo-KJo '
                      'QTo',
               'SB': '22-TT A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'},
 'OPEN_LIMP': {},
 'BB_VS_SB_LIMP': {'raise': '55+ A2s+ K8s+ Q8s+ J8s+ T8s+ 97s+ 87s A8o+ KTo+ QTo+ JTo',
                   'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s J2s-J7s '
                            'T2s-T7s 92s-96s 82s-86s 72s-75s 62s-64s 52s-54s 42s-43s 32s'},
 'VS_OPEN': {('UTG', 'MP'): {'3bet': 'JJ+ AJs+ KQs AJo+', 'call': '88-TT AJs-AQs KQs QJs JTs T9s 98s AJo-AQo KQo'},
             ('UTG', 'CO'): {'3bet': 'JJ+ AJs+ KQs AJo+', 'call': '66-TT AJs-AQs KQs QJs JTs T9s 98s AJo-AQo KQo'},
             ('UTG', 'BTN'): {'3bet': 'JJ+ AJs+ KQs AJo+',
                              'call': '44-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
             ('UTG', 'SB'): {'3bet': 'JJ+ AJs+ KQs AJo+', 'call': '22-TT AJs-AQs KQs QJs JTs T9s'},
             ('UTG', 'BB'): {'3bet': 'JJ+ AJs+ KQs AJo+',
                             'call': '22-TT A2s-AQs K7s-KQs Q7s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s A7o-AQo KTo-KQo QTo+'},
             ('MP', 'CO'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                            'call': '66-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AJo+ KQo'},
             ('MP', 'BTN'): {'3bet': 'TT+ AJs+ KQs AJo+ KQo',
                             'call': '22-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s ATo-AQo KQo'},
             ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs', 'call': '22-99 ATs-AJs KJs-KQs QJs JTs T9s'},
             ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                            'call': '22-TT A2s-AJs K7s-KQs Q8s-QJs J7s-JTs T7s-T9s 54s 65s 76s 87s 98s '
                                    'A9o-AQo KTo-KQo QJo JTo'},
             ('CO', 'BTN'): {'3bet': 'TT+ AJs+ AJo+ A2s-A5s KJs-KQs KQo',
                             'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s ATo-AQo '
                                     'KJo-KQo QJo'},
             ('CO', 'SB'): {'3bet': 'TT+ AJs+ AJo+ A2s-A5s KJs-KQs KQo',
                            'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
             ('CO', 'BB'): {'3bet': 'TT+ AJs+ AJo+ A2s-A5s KJs-KQs KQo',
                            'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s 98s '
                                    'A8o-AJo K9o-KQo Q9o-QJo JTo'},
             ('BTN', 'SB'): {'3bet': '99+ AJs+ AJo+ A2s-A5s KJs-KQs KQo QJs JTs',
                             'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s 98s ATo '
                                     'KTo-KQo QTo+ JTo'},
             ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                             'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s '
                                     'A2o-ATo K8o-KQo QTo+ JTo'},
             ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s KJs+ QJs JTs',
                            'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s '
                                    'A2o-ATo K8o-KQo QTo+ JTo'}},
 'VS_OPEN_CALLERS': {('UTG', 'CO', 1): {'3bet': 'JJ+ AQs+ AKo A5s',
                                        'call': '88-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
                     ('UTG', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s',
                                         'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s AQo'},
                     ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s', 'call': '99-TT AJs-AQs KQs QJs JTs'},
                     ('UTG', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A5s',
                                        'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                                '87s 98s ATo-AQo KJo-KQo'},
                     ('MP', 'BTN', 1): {'3bet': 'TT+ AQs+ A5s-A4s AQo+',
                                        'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s AQo KQo'},
                     ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ A5s-A4s AQo+',
                                       'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                     ('MP', 'BB', 1): {'3bet': 'TT+ AQs+ A5s-A4s AQo+',
                                       'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                               '87s 98s A9o-AQo KTo-KQo QJo'},
                     ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ A5s-A4s AQo+',
                                        'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s '
                                                'ATo-AQo KJo-KQo'},
                     ('CO', 'SB', 1): {'3bet': 'TT+ AQs+ A5s-A4s AQo+',
                                       'call': '22-99 A7s-ATs KTs-KJs QJs JTs T9s'},
                     ('CO', 'BB', 1): {'3bet': 'JJ+ AQs+ A5s-A4s AQo+',
                                       'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s '
                                               '87s 98s A8o-AJo K9o-KQo Q9o-QJo'},
                     ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                                        'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s 64s 75s 86s '
                                                '97s 98s A2o-ATo K9o-KQo QTo+ JTo'},
                     ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s', 'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
                     ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                        'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}},
 'OPENER_VS_3BET': {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                    ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                    ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                    ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
                    ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                    ('MP', 'CO'): {'4bet': 'QQ+ AQs+ AKo', 'call': 'TT-JJ AQs-AJs KQs'},
                    ('MP', 'BTN'): {'4bet': 'QQ+ AQs+ AKo', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                    ('MP', 'SB'): {'4bet': 'QQ+ AQs+ AKo', 'call': 'TT-JJ AQs-AJs KQs'},
                    ('MP', 'BB'): {'4bet': 'QQ+ AQs+ AKo', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                    ('CO', 'BTN'): {'4bet': 'JJ+ AQs+ AKo', 'call': 'TT-JJ ATs-AQs KQs QJs JTs AQo'},
                    ('CO', 'SB'): {'4bet': 'JJ+ AQs+ AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                    ('CO', 'BB'): {'4bet': 'JJ+ AQs+ AKo', 'call': 'TT-JJ ATs-AQs KQs QJs JTs AQo'},
                    ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo',
                                    'call': '99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
                    ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo',
                                    'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
                    ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                   'call': '88-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}},
 'THREEBETTER_VS_4BET': {('MP', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('CO', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BTN', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('CO', 'MP'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BTN', 'MP'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('SB', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BB', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'}},
 'COLD_4BET': {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
               ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
               ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
               ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
               ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}}

OPPONENT_PREFLOP_CHARTS = {'RFI_RAISE': {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
               'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
               'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
               'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ T9o+'},
 'SB_FIRST_IN': {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
                 'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s 53s 43s A2o+ '
                         'K2o-KJo Q8o-QJo J8o-JTo T8o 98o'},
 'ISO_RAISE': {'UTG': {},
               'MP': '88+ AJs+ KQs AQo+',
               'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
               'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
               'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
               'BB': '88+ AJs+ KQs AQo+'},
 'OVER_LIMP': {'MP': '22-88 A2s-A9s KTs QTs JTs T9s 98s',
               'CO': '22-88 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
               'BTN': '22-88 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s A8o-ATo KTo-KJo '
                      'QTo',
               'SB': '22-99 A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'},
 'OPEN_LIMP': {'MP': '22+ A2s+ K7s+ Q8s+ J7s+ T7s+ 96s+ 86s+ 75s+ 64s+ A2o+ KTo+ QTo+ JTo T9o',
               'CO': '22+ A2s+ K7s+ Q8s+ J7s+ T7s+ 96s+ 86s+ 75s+ 64s+ A2o+ KTo+ QTo+ JTo T9o',
               'BTN': '22+ A2s+ K2s+ Q2s+ J7s+ T5s+ 96s+ 86s+ 75s+ 64s+ A2o+ KTo+ QTo+ JTo T9o'},

 'BB_VS_SB_LIMP': {'raise': '22+ A2s+ K5s+ Q8s+ J8s+ T8s+ 97s+ 87s 76s 65s A8o+ KTo+ QTo+ JTo',
                   'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s J2s-J7s '
                            'T2s-T7s 92s-96s 82s-86s 72s-75s 62s-64s 52s-54s 42s-43s 32s'},

 'VS_OPEN': {('UTG', 'MP'): {'3bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs QJs JTs T9s 98s'},
             ('UTG', 'CO'): {'3bet': 'QQ+ AKs AKo A5s',
                             'call': '88-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
             ('UTG', 'BTN'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                              'call': '77-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
             ('UTG', 'SB'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs', 'call': '99-TT AJs-AQs KQs QJs JTs T9s'},
             ('UTG', 'BB'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                             'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s '
                                     'ATo-AQo KJo-KQo QJo'},
             ('MP', 'CO'): {'3bet': 'JJ+ AQs+ AKo A5s',
                            'call': '77-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AQo KQo'},
             ('MP', 'BTN'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                             'call': '55-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo KQo'},
             ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs', 'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
             ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                            'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s 98s '
                                    'A9o-AQo KTo-KQo QJo JTo'},
             ('CO', 'BTN'): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                             'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s ATo-AQo '
                                     'KJo-KQo QJo'},
             ('CO', 'SB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs QJs',
                            'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
             ('CO', 'BB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs JTs',
                            'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s 98s '
                                    'A8o-AJo K9o-KQo Q9o-QJo JTo'},
             ('BTN', 'SB'): {'3bet': '99+ ATs+ AJo+ A2s-A5s K9s-KQs QTs+ JTs T9s',
                             'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s 98s ATo '
                                     'KTo-KQo QTo+ JTo'},
             ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                             'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s '
                                     'A2o-ATo K8o-KQo QTo+ JTo'},
             ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                            'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s 97s 98s '
                                    'A2o-ATo K8o-KQo QTo+ JTo'}},
 'VS_OPEN_CALLERS': {('UTG', 'CO', 1): {'3bet': 'QQ+ AKs AKo A5s',
                                        'call': '99-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
                     ('UTG', 'BTN', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                         'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s AQo'},
                     ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s', 'call': '99-TT AJs-AQs KQs QJs JTs'},
                     ('UTG', 'BB', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                        'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                                '87s 98s ATo-AQo KJo-KQo'},
                     ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                        'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s AQo KQo'},
                     ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ AKo A5s-A4s',
                                       'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                     ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A2s-A5s',
                                       'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                               '87s 98s A9o-AQo KTo-KQo QJo'},
                     ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                        'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s '
                                                'ATo-AQo KJo-KQo'},
                     ('CO', 'SB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs',
                                       'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s'},
                     ('CO', 'BB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs',
                                       'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s '
                                               '87s 98s A8o-AJo K9o-KQo Q9o-QJo'},
                     ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                                        'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s 64s 75s 86s '
                                                '97s 98s A2o-ATo K9o-KQo QTo+ JTo'},
                     ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s', 'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
                     ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                        'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}},
 'OPENER_VS_3BET': {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': '99-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-QQ ATs+ KJs+ AJo+ KJo+'},
                    ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                    'call': '77-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
                    ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                    'call': '88-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
                    ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                   'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}},
 'THREEBETTER_VS_4BET': {('MP', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('CO', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BTN', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('CO', 'MP'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BTN', 'MP'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('SB', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BB', 'UTG'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},
                         ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'},},
 'COLD_4BET': {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
               ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
               ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
               ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
               ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}}

RANGE_PROFILES: Dict[str, Dict[str, object]] = {'hero': {'RFI_RAISE': {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
                        'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
                        'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
                        'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ T9o+'},
          'SB_FIRST_IN': {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
                          'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s 53s '
                                  '43s A2o+ K2o-KJo Q8o-QJo J8o-JTo T8o 98o'},
          'ISO_RAISE': {'UTG': {},
                        'MP': '88+ AJs+ KQs AQo+',
                        'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
                        'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
                        'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
                        'BB': '88+ AJs+ KQs AQo+'},
          'OVER_LIMP': {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
                        'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
                        'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s '
                               'A8o-ATo KTo-KJo QTo',
                        'SB': '22-55 A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'},
          'OPEN_LIMP': {},
          'BB_VS_SB_LIMP': {'raise': '22+ A2s+ K5s+ Q8s+ J8s+ T8s+ 97s+ 87s 76s 65s A8o+ KTo+ QTo+ JTo',
                            'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s '
                                     'J2s-J7s T2s-T7s 92s-96s 82s-86s 72s-75s 62s-64s 52s-54s 42s-43s 32s'},
          'VS_OPEN': {('UTG', 'MP'): {'3bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs QJs JTs T9s 98s'},
                      ('UTG', 'CO'): {'3bet': 'QQ+ AKs AKo A5s',
                                      'call': '88-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
                      ('UTG', 'BTN'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                       'call': '77-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s '
                                               'AJo-AQo KQo'},
                      ('UTG', 'SB'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                                      'call': '99-TT AJs-AQs KQs QJs JTs T9s'},
                      ('UTG', 'BB'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                      'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s '
                                              '98s ATo-AQo KJo-KQo QJo'},
                      ('MP', 'CO'): {'3bet': 'JJ+ AQs+ AKo A5s',
                                     'call': '77-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AQo KQo'},
                      ('MP', 'BTN'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                                      'call': '55-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s AJo-AQo '
                                              'KQo'},
                      ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs',
                                     'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                      ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                                     'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s 87s '
                                             '98s A9o-AQo KTo-KQo QJo JTo'},
                      ('CO', 'BTN'): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                      'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s '
                                              'ATo-AQo KJo-KQo QJo'},
                      ('CO', 'SB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs QJs',
                                     'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
                      ('CO', 'BB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs JTs',
                                     'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s 87s '
                                             '98s A8o-AJo K9o-KQo Q9o-QJo JTo'},
                      ('BTN', 'SB'): {'3bet': '99+ ATs+ AJo+ A2s-A5s K9s-KQs QTs+ JTs T9s',
                                      'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s 98s '
                                              'ATo KTo-KQo QTo+ JTo'},
                      ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                                      'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s '
                                              '97s 98s A2o-ATo K8o-KQo QTo+ JTo'},
                      ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                                     'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s 86s '
                                             '97s 98s A2o-ATo K8o-KQo QTo+ JTo'}},
          'VS_OPEN_CALLERS': {('UTG', 'CO', 1): {'3bet': 'QQ+ AKs AKo A5s',
                                                 'call': '99-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
                              ('UTG', 'BTN', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                                  'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s '
                                                          'AQo'},
                              ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                 'call': '99-TT AJs-AQs KQs QJs JTs'},
                              ('UTG', 'BB', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                                 'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s '
                                                         '65s 76s 87s 98s ATo-AQo KJo-KQo'},
                              ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                 'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s AQo '
                                                         'KQo'},
                              ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ AKo A5s-A4s',
                                                'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                              ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A2s-A5s',
                                                'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s '
                                                        '65s 76s 87s 98s A9o-AQo KTo-KQo QJo'},
                              ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                                 'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s '
                                                         '76s ATo-AQo KJo-KQo'},
                              ('CO', 'SB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs',
                                                'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s'},
                              ('CO', 'BB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs',
                                                'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s '
                                                        '65s 76s 87s 98s A8o-AJo K9o-KQo Q9o-QJo'},
                              ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                                                 'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s 64s '
                                                         '75s 86s 97s 98s A2o-ATo K9o-KQo QTo+ JTo'},
                              ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s',
                                                'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
                              ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                 'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}},
          'OPENER_VS_3BET': {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                             ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                             ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                             ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
                             ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                             ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
                             ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                             ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
                             ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                             ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s',
                                             'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
                             ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs'},
                             ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s',
                                            'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
                             ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                             'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
                             ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                             'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo KQo'},
                             ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                            'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}},
          'THREEBETTER_VS_4BET': {('MP', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('CO', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('BTN', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('CO', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('BTN', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('SB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('BB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                  ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                  ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                  ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                  ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'}},
          'COLD_4BET': {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                        ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                        ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                        ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
                        ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}},
 'opponent': {'RFI_RAISE': {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
                            'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
                            'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
                            'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ '
                                   'T9o+'},
              'SB_FIRST_IN': {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
                              'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s '
                                      '53s 43s A2o+ K2o-KJo Q8o-QJo J8o-JTo T8o 98o'},
              'ISO_RAISE': {'UTG': {},
                            'MP': '88+ AJs+ KQs AQo+',
                            'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
                            'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
                            'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
                            'BB': '88+ AJs+ KQs AQo+'},
              'OVER_LIMP': {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
                            'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
                            'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s '
                                   'A8o-ATo KTo-KJo QTo',
                            'SB': '22-55 A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'},
              'OPEN_LIMP': {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
                            'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
                            'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s '
                                   'A8o-ATo KTo-KJo QTo'},
              'BB_VS_SB_LIMP': {'raise': '22+ A2s+ K5s+ Q8s+ J8s+ T8s+ 97s+ 87s 76s 65s A8o+ KTo+ QTo+ JTo',
                                'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s '
                                         'Q2s-Q7s J2s-J7s T2s-T7s 92s-96s 82s-86s 72s-75s 62s-64s 52s-54s '
                                         '42s-43s 32s'},
              'VS_OPEN': {('UTG', 'MP'): {'3bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs QJs JTs T9s 98s'},
                          ('UTG', 'CO'): {'3bet': 'QQ+ AKs AKo A5s',
                                          'call': '88-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
                          ('UTG', 'BTN'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                           'call': '77-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s '
                                                   'AJo-AQo KQo'},
                          ('UTG', 'SB'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                                          'call': '99-TT AJs-AQs KQs QJs JTs T9s'},
                          ('UTG', 'BB'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                          'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                                  '87s 98s ATo-AQo KJo-KQo QJo'},
                          ('MP', 'CO'): {'3bet': 'JJ+ AQs+ AKo A5s',
                                         'call': '77-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AQo KQo'},
                          ('MP', 'BTN'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                                          'call': '55-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s '
                                                  'AJo-AQo KQo'},
                          ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs',
                                         'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                          ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                                         'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                                 '87s 98s A9o-AQo KTo-KQo QJo JTo'},
                          ('CO', 'BTN'): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                          'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s '
                                                  'ATo-AQo KJo-KQo QJo'},
                          ('CO', 'SB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs QJs',
                                         'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
                          ('CO', 'BB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs JTs',
                                         'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s '
                                                 '87s 98s A8o-AJo K9o-KQo Q9o-QJo JTo'},
                          ('BTN', 'SB'): {'3bet': '99+ ATs+ AJo+ A2s-A5s K9s-KQs QTs+ JTs T9s',
                                          'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s '
                                                  '98s ATo KTo-KQo QTo+ JTo'},
                          ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                                          'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s '
                                                  '86s 97s 98s A2o-ATo K8o-KQo QTo+ JTo'},
                          ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                                         'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s '
                                                 '86s 97s 98s A2o-ATo K8o-KQo QTo+ JTo'}},
              'VS_OPEN_CALLERS': {('UTG', 'CO', 1): {'3bet': 'QQ+ AKs AKo A5s',
                                                     'call': '99-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
                                  ('UTG', 'BTN', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                                      'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s '
                                                              'AQo'},
                                  ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                     'call': '99-TT AJs-AQs KQs QJs JTs'},
                                  ('UTG', 'BB', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                                     'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s '
                                                             '54s 65s 76s 87s 98s ATo-AQo KJo-KQo'},
                                  ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                     'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s '
                                                             'AQo KQo'},
                                  ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ AKo A5s-A4s',
                                                    'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                                  ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A2s-A5s',
                                                    'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s '
                                                            '54s 65s 76s 87s 98s A9o-AQo KTo-KQo QJo'},
                                  ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                                     'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s '
                                                             '87s 76s ATo-AQo KJo-KQo'},
                                  ('CO', 'SB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs',
                                                    'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s'},
                                  ('CO', 'BB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs',
                                                    'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s '
                                                            '54s 65s 76s 87s 98s A8o-AJo K9o-KQo Q9o-QJo'},
                                  ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                                                     'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s '
                                                             '64s 75s 86s 97s 98s A2o-ATo K9o-KQo QTo+ JTo'},
                                  ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s',
                                                    'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
                                  ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                     'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}},
              'OPENER_VS_3BET': {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                                 ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                                 ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                                 ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
                                 ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                                 ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
                                 ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                                 ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
                                 ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                                 ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s',
                                                 'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
                                 ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs'},
                                 ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s',
                                                'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
                                 ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo '
                                                         'KQo'},
                                 ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                                 'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo '
                                                         'KQo'},
                                 ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                                'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}},
              'THREEBETTER_VS_4BET': {('MP', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('CO', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('BTN', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('CO', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('BTN', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('SB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('BB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                      ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                      ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                      ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                      ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'}},
              'COLD_4BET': {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                            ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                            ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                            ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
                            ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}},
 'villain': {'RFI_RAISE': {'UTG': '22+ A5s+ KTs+ QTs+ J9s+ T8s+ 98s+ ATo+ KJo+ QJo+',
                           'MP': '22+ A2s+ K9s+ Q9s+ J8s+ T8s+ 97s+ A9o+ KTo+ QTo+',
                           'CO': '22+ A2s+ K8s+ Q7s+ J7s+ T7s+ 97s+ 86s+ 76s+ A8o+ KTo+ QTo+',
                           'BTN': '22+ A2s+ K5s+ Q6s+ J7s+ T6s+ 96s+ 85s+ 76s+ 65s+ A2o+ K8o+ Q8o+ J9o+ '
                                  'T9o+'},
             'SB_FIRST_IN': {'raise': '88+ A7s+ KTs+ QJs+ JTs+ T9s+ A9o+ KJo+ QJo+',
                             'limp': '22+ A2s+ K2s-KQs Q2s-QJs J2s-JTs T2s-T9s 92s-98s 82s-87s 72s-76s 63s '
                                     '53s 43s A2o+ K2o-KJo Q8o-QJo J8o-JTo T8o 98o'},
             'ISO_RAISE': {'UTG': {},
                           'MP': '88+ AJs+ KQs AQo+',
                           'CO': '77+ ATs+ KJs+ QJs JTs AJo+ KQo',
                           'BTN': '66+ A8s+ KTs+ QTs+ JTs T9s 98s ATo+ KJo+ QJo',
                           'SB': '77+ ATs+ KTs+ QTs+ JTs AJo+ KQo',
                           'BB': '88+ AJs+ KQs AQo+'},
             'OVER_LIMP': {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
                           'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
                           'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s '
                                  'A8o-ATo KTo-KJo QTo',
                           'SB': '22-55 A2s-A6s K9s-KTs Q9s-QTs JTs T9s 98s'},
             'OPEN_LIMP': {'MP': '22-77 A2s-A9s KTs QTs JTs T9s 98s',
                           'CO': '22-66 A2s-A7s K9s-KTs Q9s-QTs J9s-JTs T9s 98s 87s A9o-ATo KTo QTo',
                           'BTN': '22-66 A2s-A7s K8s-KTs Q8s-QTs J8s-JTs T8s-T9s 97s-98s 86s-87s 76s 65s '
                                  'A8o-ATo KTo-KJo QTo'},
             'BB_VS_SB_LIMP': {'raise': '22+ A2s+ K5s+ Q8s+ J8s+ T8s+ 97s+ 87s 76s 65s A8o+ KTo+ QTo+ JTo',
                               'check': 'A2o-A7o K2o-K9o Q5o-Q9o J7o-J9o T7o-T9o 98o 87o 76o K2s-K4s Q2s-Q7s '
                                        'J2s-J7s T2s-T7s 92s-96s 82s-86s 72s-75s 62s-64s 52s-54s 42s-43s '
                                        '32s'},
             'VS_OPEN': {('UTG', 'MP'): {'3bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs QJs JTs T9s 98s'},
                         ('UTG', 'CO'): {'3bet': 'QQ+ AKs AKo A5s',
                                         'call': '88-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
                         ('UTG', 'BTN'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                          'call': '77-JJ A9s-AQs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s '
                                                  'AJo-AQo KQo'},
                         ('UTG', 'SB'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                                         'call': '99-TT AJs-AQs KQs QJs JTs T9s'},
                         ('UTG', 'BB'): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                         'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                                 '87s 98s ATo-AQo KJo-KQo QJo'},
                         ('MP', 'CO'): {'3bet': 'JJ+ AQs+ AKo A5s',
                                        'call': '77-TT ATs-AQs KJs-KQs QJs JTs T9s 98s AQo KQo'},
                         ('MP', 'BTN'): {'3bet': 'JJ+ AQs+ AKo A5s-A4s KQs',
                                         'call': '55-TT A8s-AJs KTs-KQs QTs-QJs J9s-JTs T9s 98s 87s 76s '
                                                 'AJo-AQo KQo'},
                         ('MP', 'SB'): {'3bet': 'TT+ AQs+ AKo A5s-A4s KQs',
                                        'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                         ('MP', 'BB'): {'3bet': 'JJ+ AQs+ AKo A2s-A5s KQs',
                                        'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 54s 65s 76s '
                                                '87s 98s A9o-AQo KTo-KQo QJo JTo'},
                         ('CO', 'BTN'): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                         'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s 87s 76s 65s '
                                                 'ATo-AQo KJo-KQo QJo'},
                         ('CO', 'SB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs QJs',
                                        'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s 98s'},
                         ('CO', 'BB'): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs JTs',
                                        'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s 54s 65s 76s '
                                                '87s 98s A8o-AJo K9o-KQo Q9o-QJo JTo'},
                         ('BTN', 'SB'): {'3bet': '99+ ATs+ AJo+ A2s-A5s K9s-KQs QTs+ JTs T9s',
                                         'call': '22-88 A2s-A9s K8s-KJs Q9s-QJs J8s-JTs T8s-T9s 65s 76s 87s '
                                                 '98s ATo KTo-KQo QTo+ JTo'},
                         ('BTN', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                                         'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s '
                                                 '86s 97s 98s A2o-ATo K8o-KQo QTo+ JTo'},
                         ('SB', 'BB'): {'3bet': '88+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s 98s',
                                        'call': '22-77 A2s-A9s K4s-KJs Q7s-QJs J7s-JTs T7s-T9s 53s 64s 75s '
                                                '86s 97s 98s A2o-ATo K8o-KQo QTo+ JTo'}},
             'VS_OPEN_CALLERS': {('UTG', 'CO', 1): {'3bet': 'QQ+ AKs AKo A5s',
                                                    'call': '99-JJ AJs-AQs KQs QJs JTs T9s 98s 87s AQo'},
                                 ('UTG', 'BTN', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                                     'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s 76s '
                                                             'AQo'},
                                 ('UTG', 'SB', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                    'call': '99-TT AJs-AQs KQs QJs JTs'},
                                 ('UTG', 'BB', 1): {'3bet': 'QQ+ AKs AKo A5s-A4s',
                                                    'call': '22-JJ A2s-AQs KTs-KQs QTs-QJs J8s-JTs T8s-T9s '
                                                            '54s 65s 76s 87s 98s ATo-AQo KJo-KQo'},
                                 ('MP', 'BTN', 1): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                    'call': '66-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s 87s '
                                                            'AQo KQo'},
                                 ('MP', 'SB', 1): {'3bet': 'TT+ AQs+ AKo A5s-A4s',
                                                   'call': '77-99 ATs-AJs KJs-KQs QJs JTs T9s'},
                                 ('MP', 'BB', 1): {'3bet': 'JJ+ AQs+ AKo A2s-A5s',
                                                   'call': '22-TT A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s '
                                                           '54s 65s 76s 87s 98s A9o-AQo KTo-KQo QJo'},
                                 ('CO', 'BTN', 1): {'3bet': 'TT+ AQs+ AKo A2s-A5s KJs-KQs',
                                                    'call': '22-99 A2s-AJs KTs-KQs QTs-QJs J8s-JTs T9s 98s '
                                                            '87s 76s ATo-AQo KJo-KQo'},
                                 ('CO', 'SB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s KTs-KQs',
                                                   'call': '55-99 A7s-ATs KTs-KJs QJs JTs T9s'},
                                 ('CO', 'BB', 1): {'3bet': 'TT+ AJs+ AQo+ A2s-A5s K9s-KQs QTs-QJs',
                                                   'call': '22-99 A2s-ATs K7s-KJs Q8s-QJs J7s-JTs T8s-T9s '
                                                           '54s 65s 76s 87s 98s A8o-AJo K9o-KQo Q9o-QJo'},
                                 ('BTN', 'BB', 1): {'3bet': '99+ ATs+ AJo+ A2s-A5s K8s-KQs QTs+ JTs T9s',
                                                    'call': '22-88 A2s-A9s K5s-KJs Q8s-QJs J8s-JTs T8s-T9s '
                                                            '64s 75s 86s 97s 98s A2o-ATo K9o-KQo QTo+ JTo'},
                                 ('CO', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s',
                                                   'call': '66-JJ AJs-AQs KQs QJs JTs T9s'},
                                 ('BTN', 'BB', 2): {'3bet': 'JJ+ AQs+ AKo A5s-A4s',
                                                    'call': '55-TT A9s-AJs KTs-KQs QTs-QJs JTs T9s 98s'}},
             'OPENER_VS_3BET': {('UTG', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                                ('UTG', 'CO'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs-AJs KQs'},
                                ('UTG', 'BTN'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                                ('UTG', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ-TT AQs KQs'},
                                ('UTG', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'TT-JJ AJs-AQs KQs'},
                                ('MP', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
                                ('MP', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                                ('MP', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AQs-AJs KQs'},
                                ('MP', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'TT-JJ AJs-AQs KQs QJs'},
                                ('CO', 'BTN'): {'4bet': 'QQ+ AKs AKo A5s-A4s',
                                                'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
                                ('CO', 'SB'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs'},
                                ('CO', 'BB'): {'4bet': 'QQ+ AKs AKo A5s-A4s',
                                               'call': '88-JJ ATs-AQs KQs QJs JTs AQo'},
                                ('BTN', 'SB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                                'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo '
                                                        'KQo'},
                                ('BTN', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                                'call': '55-99 A2s-AJs KTs-KQs QTs-QJs JTs T9s 98s AJo-AQo '
                                                        'KQo'},
                                ('SB', 'BB'): {'4bet': 'TT+ AQs+ AKo A2s-A5s',
                                               'call': '66-99 A7s-AJs KTs-KQs QJs JTs T9s 98s AQo'}},
             'THREEBETTER_VS_4BET': {('MP', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('CO', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('BTN', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('CO', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('BTN', 'MP'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('SB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('BB', 'UTG'): {'5bet_jam': 'KK+ AKs AKo', 'call': 'QQ'},
                                     ('SB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                     ('BB', 'BTN'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                     ('BB', 'SB'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'},
                                     ('BTN', 'CO'): {'5bet_jam': 'QQ+ AKs AKo A5s-A4s', 'call': 'JJ AQs'}},
             'COLD_4BET': {('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                           ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                           ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ'},
                           ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
                           ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'}}}}


# -----------------------------------------------------------------------------
# Added branch: limper vs iso (approved ranges)
# -----------------------------------------------------------------------------

HERO_LIMPER_VS_ISO: Dict[Tuple[str, str], Dict[str, str]] = {
    ('SB', 'BB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K7s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    }
}

OPPONENT_LIMPER_VS_ISO: Dict[Tuple[str, str], Dict[str, str]] = {
    ('SB', 'BB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    }
}

HERO_PREFLOP_CHARTS['LIMPER_VS_ISO'] = HERO_LIMPER_VS_ISO
OPPONENT_PREFLOP_CHARTS['LIMPER_VS_ISO'] = OPPONENT_LIMPER_VS_ISO


# -----------------------------------------------------------------------------
# Final profile bindings used by the advisor
# -----------------------------------------------------------------------------

HERO_RFI_RAISE = HERO_PREFLOP_CHARTS["RFI_RAISE"]
HERO_SB_FIRST_IN = HERO_PREFLOP_CHARTS["SB_FIRST_IN"]
HERO_ISO_RAISE = HERO_PREFLOP_CHARTS["ISO_RAISE"]
HERO_OVER_LIMP = HERO_PREFLOP_CHARTS["OVER_LIMP"]
HERO_OPEN_LIMP = HERO_PREFLOP_CHARTS["OPEN_LIMP"]
HERO_BB_VS_SB_LIMP = HERO_PREFLOP_CHARTS["BB_VS_SB_LIMP"]
HERO_VS_OPEN = HERO_PREFLOP_CHARTS["VS_OPEN"]
HERO_VS_OPEN_CALLERS = HERO_PREFLOP_CHARTS["VS_OPEN_CALLERS"]
HERO_OPENER_VS_3BET = HERO_PREFLOP_CHARTS["OPENER_VS_3BET"]
HERO_THREEBETTER_VS_4BET = HERO_PREFLOP_CHARTS["THREEBETTER_VS_4BET"]
HERO_COLD_4BET = HERO_PREFLOP_CHARTS["COLD_4BET"]
HERO_LIMPER_VS_ISO = HERO_PREFLOP_CHARTS["LIMPER_VS_ISO"]

OPPONENT_RFI_RAISE = OPPONENT_PREFLOP_CHARTS["RFI_RAISE"]
OPPONENT_SB_FIRST_IN = OPPONENT_PREFLOP_CHARTS["SB_FIRST_IN"]
OPPONENT_ISO_RAISE = OPPONENT_PREFLOP_CHARTS["ISO_RAISE"]
OPPONENT_OVER_LIMP = OPPONENT_PREFLOP_CHARTS["OVER_LIMP"]
OPPONENT_OPEN_LIMP = OPPONENT_PREFLOP_CHARTS["OPEN_LIMP"]
OPPONENT_BB_VS_SB_LIMP = OPPONENT_PREFLOP_CHARTS["BB_VS_SB_LIMP"]
OPPONENT_VS_OPEN = OPPONENT_PREFLOP_CHARTS["VS_OPEN"]
OPPONENT_VS_OPEN_CALLERS = OPPONENT_PREFLOP_CHARTS["VS_OPEN_CALLERS"]
OPPONENT_OPENER_VS_3BET = OPPONENT_PREFLOP_CHARTS["OPENER_VS_3BET"]
OPPONENT_THREEBETTER_VS_4BET = OPPONENT_PREFLOP_CHARTS["THREEBETTER_VS_4BET"]
OPPONENT_COLD_4BET = OPPONENT_PREFLOP_CHARTS["COLD_4BET"]
OPPONENT_LIMPER_VS_ISO = OPPONENT_PREFLOP_CHARTS["LIMPER_VS_ISO"]

# Shared baseline exports keep the opponent / pool defaults.
RFI_RAISE = OPPONENT_RFI_RAISE
OPEN_LIMP = OPPONENT_OPEN_LIMP
SB_FIRST_IN = OPPONENT_SB_FIRST_IN
ISO_RAISE = OPPONENT_ISO_RAISE
OVER_LIMP = OPPONENT_OVER_LIMP
BB_VS_SB_LIMP = OPPONENT_BB_VS_SB_LIMP
VS_OPEN = OPPONENT_VS_OPEN
VS_OPEN_CALLERS = OPPONENT_VS_OPEN_CALLERS
OPENER_VS_3BET = OPPONENT_OPENER_VS_3BET
THREEBETTER_VS_4BET = OPPONENT_THREEBETTER_VS_4BET
COLD_4BET = OPPONENT_COLD_4BET
LIMPER_VS_ISO = OPPONENT_LIMPER_VS_ISO

RANGE_PROFILES = {
    "hero": HERO_PREFLOP_CHARTS,
    "opponent": OPPONENT_PREFLOP_CHARTS,
    "villain": OPPONENT_PREFLOP_CHARTS,
}

__all__ = ['RFI_RAISE',
 'OPEN_LIMP',
 'SB_FIRST_IN',
 'ISO_RAISE',
 'OVER_LIMP',
 'BB_VS_SB_LIMP',
 'VS_OPEN',
 'VS_OPEN_CALLERS',
 'OPENER_VS_3BET',
 'THREEBETTER_VS_4BET',
 'COLD_4BET',
 'LIMPER_VS_ISO',
 'HERO_RFI_RAISE',
 'HERO_SB_FIRST_IN',
 'HERO_ISO_RAISE',
 'HERO_OVER_LIMP',
 'HERO_OPEN_LIMP',
 'HERO_BB_VS_SB_LIMP',
 'HERO_VS_OPEN',
 'HERO_VS_OPEN_CALLERS',
 'HERO_OPENER_VS_3BET',
 'HERO_THREEBETTER_VS_4BET',
 'HERO_COLD_4BET',
 'HERO_LIMPER_VS_ISO',
 'OPPONENT_RFI_RAISE',
 'OPPONENT_SB_FIRST_IN',
 'OPPONENT_ISO_RAISE',
 'OPPONENT_OVER_LIMP',
 'OPPONENT_OPEN_LIMP',
 'OPPONENT_BB_VS_SB_LIMP',
 'OPPONENT_VS_OPEN',
 'OPPONENT_VS_OPEN_CALLERS',
 'OPPONENT_OPENER_VS_3BET',
 'OPPONENT_THREEBETTER_VS_4BET',
 'OPPONENT_COLD_4BET',
 'OPPONENT_LIMPER_VS_ISO',
 'HERO_PREFLOP_CHARTS',
 'OPPONENT_PREFLOP_CHARTS',
 'RANGE_PROFILES']


# =============================================================================
# Runtime patch block: complete missing preflop coverage
# =============================================================================

def _merge_action_map(existing: dict, new_items: dict) -> dict:
    merged = dict(existing)
    merged.update(new_items)
    return merged

# limper_vs_iso: premium hands limp/3bet, the rest continue by call as requested
_HERO_LIMPER_VS_ISO_PATCH: Dict[Tuple[str, str], Dict[str, str]] = {
    ('MP', 'CO'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('MP', 'BTN'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('MP', 'SB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('MP', 'BB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('CO', 'BTN'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('CO', 'SB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('CO', 'BB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('BTN', 'SB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K7s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('BTN', 'BB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K7s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('SB', 'BB'): {
        '3bet': 'QQ+ AQs+ AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K7s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AQo KTo-KQo QTo-QJo JTo',
    },
}

_OPPONENT_LIMPER_VS_ISO_PATCH: Dict[Tuple[str, str], Dict[str, str]] = {
    ('MP', 'CO'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('MP', 'BTN'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('MP', 'SB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('MP', 'BB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-JJ A2s-AJs K9s-KQs Q9s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A9o-AQo KTo-KQo QTo-QJo JTo',
    },
    ('CO', 'BTN'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    },
    ('CO', 'SB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    },
    ('CO', 'BB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    },
    ('BTN', 'SB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K7s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    },
    ('BTN', 'BB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K7s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    },
    ('SB', 'BB'): {
        '3bet': 'KK+ AKs AKo A5s-A4s',
        'call': '22-TT A2s-AJs K8s-KQs Q8s-QJs J8s-JTs T8s-T9s 97s+ 86s+ 75s+ 64s+ 54s A8o-AJo KTo-KQo QTo-QJo JTo',
    },
}
HERO_PREFLOP_CHARTS['LIMPER_VS_ISO'] = _merge_action_map(HERO_PREFLOP_CHARTS.get('LIMPER_VS_ISO', {}), _HERO_LIMPER_VS_ISO_PATCH)
OPPONENT_PREFLOP_CHARTS['LIMPER_VS_ISO'] = _merge_action_map(OPPONENT_PREFLOP_CHARTS.get('LIMPER_VS_ISO', {}), _OPPONENT_LIMPER_VS_ISO_PATCH)

# facing_open_callers bucket=2: fill missing practical branches
_HERO_VS_OPEN_CALLERS_PATCH: Dict[Tuple[str, str, int], Dict[str, str]] = {
    ('UTG', 'BTN', 2): {'3bet': 'QQ+ AKs AKo A5s-A4s', 'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
    ('UTG', 'SB', 2): {'3bet': 'QQ+ AKs AKo A5s-A4s', 'call': '99-JJ AJs-AQs KQs QJs JTs'},
    ('UTG', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s-A4s', 'call': '77-JJ ATs-AQs KJs-KQs QJs JTs T9s 98s 87s AQo'},
    ('MP', 'SB', 2): {'3bet': 'QQ+ AKs AKo A5s-A4s', 'call': '88-JJ AJs-AQs KQs QJs JTs T9s'},
    ('MP', 'BB', 2): {'3bet': 'QQ+ AKs AKo A5s-A4s', 'call': '66-JJ A9s-AQs KTs-KQs QTs-QJs JTs T9s 98s AQo KQo'},
}
_OPPONENT_VS_OPEN_CALLERS_PATCH = dict(_HERO_VS_OPEN_CALLERS_PATCH)
HERO_PREFLOP_CHARTS['VS_OPEN_CALLERS'] = _merge_action_map(HERO_PREFLOP_CHARTS.get('VS_OPEN_CALLERS', {}), _HERO_VS_OPEN_CALLERS_PATCH)
OPPONENT_PREFLOP_CHARTS['VS_OPEN_CALLERS'] = _merge_action_map(OPPONENT_PREFLOP_CHARTS.get('VS_OPEN_CALLERS', {}), _OPPONENT_VS_OPEN_CALLERS_PATCH)

# cold_4bet: fill missing practical branches
_HERO_COLD_4BET_PATCH: Dict[Tuple[str, str, str], Dict[str, str]] = {
    ('UTG', 'MP', 'CO'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'MP', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'MP', 'SB'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'MP', 'BB'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'CO', 'SB'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'CO', 'BB'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('UTG', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ AQs'},
    ('UTG', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ AQs'},
    ('MP', 'CO', 'BTN'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('MP', 'CO', 'SB'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('MP', 'CO', 'BB'): {'4bet': 'KK+ AKs AKo', 'call': 'QQ'},
    ('MP', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ AQs'},
    ('MP', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ AQs'},
    ('CO', 'BTN', 'SB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'JJ AQs'},
    ('CO', 'BTN', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'JJ AQs'},
    ('BTN', 'SB', 'BB'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'JJ AQs'},
}
_OPPONENT_COLD_4BET_PATCH = dict(_HERO_COLD_4BET_PATCH)
HERO_PREFLOP_CHARTS['COLD_4BET'] = _merge_action_map(HERO_PREFLOP_CHARTS.get('COLD_4BET', {}), _HERO_COLD_4BET_PATCH)
OPPONENT_PREFLOP_CHARTS['COLD_4BET'] = _merge_action_map(OPPONENT_PREFLOP_CHARTS.get('COLD_4BET', {}), _OPPONENT_COLD_4BET_PATCH)

# Rebind final aliases after patching
HERO_VS_OPEN_CALLERS = HERO_PREFLOP_CHARTS['VS_OPEN_CALLERS']
OPPONENT_VS_OPEN_CALLERS = OPPONENT_PREFLOP_CHARTS['VS_OPEN_CALLERS']
VS_OPEN_CALLERS = OPPONENT_VS_OPEN_CALLERS
HERO_COLD_4BET = HERO_PREFLOP_CHARTS['COLD_4BET']
OPPONENT_COLD_4BET = OPPONENT_PREFLOP_CHARTS['COLD_4BET']
COLD_4BET = OPPONENT_COLD_4BET
HERO_LIMPER_VS_ISO = HERO_PREFLOP_CHARTS['LIMPER_VS_ISO']
OPPONENT_LIMPER_VS_ISO = OPPONENT_PREFLOP_CHARTS['LIMPER_VS_ISO']
LIMPER_VS_ISO = OPPONENT_LIMPER_VS_ISO
RANGE_PROFILES['hero'] = HERO_PREFLOP_CHARTS
RANGE_PROFILES['opponent'] = OPPONENT_PREFLOP_CHARTS
RANGE_PROFILES['villain'] = OPPONENT_PREFLOP_CHARTS
for _name in (
    'LIMPER_VS_ISO','HERO_LIMPER_VS_ISO','OPPONENT_LIMPER_VS_ISO',
    'HERO_COLD_4BET','OPPONENT_COLD_4BET','HERO_VS_OPEN_CALLERS','OPPONENT_VS_OPEN_CALLERS',
):
    if _name not in __all__:
        __all__.append(_name)


# =============================================================================
# Runtime patch block 2: residual 100-hand coverage
# =============================================================================
_HERO_COLD_4BET_PATCH_2: Dict[Tuple[str, str, str], Dict[str, str]] = {
    ('CO', 'BTN', 'MP'): {'4bet': 'QQ+ AKs AKo', 'call': 'JJ AQs'},
    ('BTN', 'BB', 'MP'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'JJ AQs'},
    ('BTN', 'BB', 'CO'): {'4bet': 'QQ+ AKs AKo A5s', 'call': 'JJ AQs'},
}
_OPPONENT_COLD_4BET_PATCH_2 = dict(_HERO_COLD_4BET_PATCH_2)
HERO_PREFLOP_CHARTS['COLD_4BET'] = _merge_action_map(HERO_PREFLOP_CHARTS.get('COLD_4BET', {}), _HERO_COLD_4BET_PATCH_2)
OPPONENT_PREFLOP_CHARTS['COLD_4BET'] = _merge_action_map(OPPONENT_PREFLOP_CHARTS.get('COLD_4BET', {}), _OPPONENT_COLD_4BET_PATCH_2)

_HERO_OPENER_VS_3BET_PATCH_2: Dict[Tuple[str, str], Dict[str, str]] = {
    ('BTN', 'MP'): {'4bet': 'QQ+ AKs AKo A5s-A4s', 'call': 'TT-JJ AJs-AQs KQs'},
}
_OPPONENT_OPENER_VS_3BET_PATCH_2 = dict(_HERO_OPENER_VS_3BET_PATCH_2)
HERO_PREFLOP_CHARTS['OPENER_VS_3BET'] = _merge_action_map(HERO_PREFLOP_CHARTS.get('OPENER_VS_3BET', {}), _HERO_OPENER_VS_3BET_PATCH_2)
OPPONENT_PREFLOP_CHARTS['OPENER_VS_3BET'] = _merge_action_map(OPPONENT_PREFLOP_CHARTS.get('OPENER_VS_3BET', {}), _OPPONENT_OPENER_VS_3BET_PATCH_2)

HERO_COLD_4BET = HERO_PREFLOP_CHARTS['COLD_4BET']
OPPONENT_COLD_4BET = OPPONENT_PREFLOP_CHARTS['COLD_4BET']
COLD_4BET = OPPONENT_COLD_4BET
HERO_OPENER_VS_3BET = HERO_PREFLOP_CHARTS['OPENER_VS_3BET']
OPPONENT_OPENER_VS_3BET = OPPONENT_PREFLOP_CHARTS['OPENER_VS_3BET']
OPENER_VS_3BET = OPPONENT_OPENER_VS_3BET
RANGE_PROFILES['hero'] = HERO_PREFLOP_CHARTS
RANGE_PROFILES['opponent'] = OPPONENT_PREFLOP_CHARTS
RANGE_PROFILES['villain'] = OPPONENT_PREFLOP_CHARTS


# =============================================================================
# Runtime patch block 3: final logical normalization for 6-max GUI coverage
# =============================================================================

_FINAL_PREFLOP_ORDER = ("UTG", "MP", "CO", "BTN", "SB", "BB")
_FINAL_PREFLOP_INDEX = {pos: idx for idx, pos in enumerate(_FINAL_PREFLOP_ORDER)}


def _final_copy_actions(action_map: Dict[str, str]) -> Dict[str, str]:
    return {str(action): str(expr) for action, expr in dict(action_map).items()}


def _final_valid_cold_4bet_keys() -> set[tuple[str, str, str]]:
    out: set[tuple[str, str, str]] = set()
    for open_idx, opener in enumerate(_FINAL_PREFLOP_ORDER[:-1]):
        for three_idx in range(open_idx + 1, len(_FINAL_PREFLOP_ORDER) - 1):
            threebettor = _FINAL_PREFLOP_ORDER[three_idx]
            for hero_idx in range(three_idx + 1, len(_FINAL_PREFLOP_ORDER)):
                hero = _FINAL_PREFLOP_ORDER[hero_idx]
                out.add((opener, threebettor, hero))
    return out


def _final_valid_limper_vs_iso_keys() -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for limp_idx, limper in enumerate(_FINAL_PREFLOP_ORDER[:-1]):
        for iso_idx in range(limp_idx + 1, len(_FINAL_PREFLOP_ORDER)):
            out.add((limper, _FINAL_PREFLOP_ORDER[iso_idx]))
    return out


def _final_valid_threebettor_vs_4bet_pairs() -> set[tuple[str, str]]:
    valid = set()
    # opener 4bets
    for open_idx, opener in enumerate(_FINAL_PREFLOP_ORDER[:-1]):
        for three_idx in range(open_idx + 1, len(_FINAL_PREFLOP_ORDER)):
            valid.add((_FINAL_PREFLOP_ORDER[three_idx], opener))
    # cold 4bettor 4bets
    for opener, threebettor, hero in _final_valid_cold_4bet_keys():
        valid.add((threebettor, hero))
    return valid


def _complete_profile(profile: Dict[str, object]) -> Dict[str, object]:
    charts = dict(profile)

    # 1) limper_vs_iso: complete all valid limper -> iso branches; UTG branches mirror the closest MP templates.
    limper_vs_iso = dict(charts.get('LIMPER_VS_ISO') or {})
    valid_limper_vs_iso = _final_valid_limper_vs_iso_keys()
    for key in sorted(valid_limper_vs_iso):
        if key in limper_vs_iso:
            continue
        hero_pos, iso_pos = key
        same_hero_candidates = [cand for cand in limper_vs_iso if cand[0] == hero_pos]
        if same_hero_candidates:
            same_hero_candidates.sort(key=lambda cand: abs(_FINAL_PREFLOP_INDEX[cand[1]] - _FINAL_PREFLOP_INDEX[iso_pos]))
            limper_vs_iso[key] = _final_copy_actions(limper_vs_iso[same_hero_candidates[0]])
            continue
        base_hero = 'MP' if hero_pos == 'UTG' else hero_pos
        base_key = (base_hero, iso_pos)
        if base_key in limper_vs_iso:
            limper_vs_iso[key] = _final_copy_actions(limper_vs_iso[base_key])
            continue
        same_iso_candidates = [cand for cand in limper_vs_iso if cand[1] == iso_pos]
        if same_iso_candidates:
            same_iso_candidates.sort(key=lambda cand: abs(_FINAL_PREFLOP_INDEX[cand[0]] - _FINAL_PREFLOP_INDEX[hero_pos]))
            limper_vs_iso[key] = _final_copy_actions(limper_vs_iso[same_iso_candidates[0]])
    charts['LIMPER_VS_ISO'] = {key: limper_vs_iso[key] for key in sorted(limper_vs_iso)}

    # 2) cold_4bet: keep only valid keys and add the missing SB->BB branches from the nearest existing analogues.
    cold_4bet = {key: _final_copy_actions(value) for key, value in dict(charts.get('COLD_4BET') or {}).items() if key in _final_valid_cold_4bet_keys()}
    cold_templates = {
        ('UTG', 'SB', 'BB'): cold_4bet.get(('UTG', 'CO', 'BB')) or cold_4bet.get(('UTG', 'MP', 'BB')),
        ('MP', 'SB', 'BB'): cold_4bet.get(('MP', 'CO', 'BB')) or cold_4bet.get(('MP', 'BTN', 'BB')),
        ('CO', 'SB', 'BB'): cold_4bet.get(('CO', 'BTN', 'BB')) or cold_4bet.get(('CO', 'BTN', 'SB')),
    }
    for key, template in cold_templates.items():
        if key not in cold_4bet and template:
            cold_4bet[key] = _final_copy_actions(template)
    charts['COLD_4BET'] = {key: cold_4bet[key] for key in sorted(cold_4bet)}

    # 3) threebettor_vs_4bet: make the coverage complete for every valid 3bet/4bet pair.
    threebettor_vs_4bet = {key: _final_copy_actions(value) for key, value in dict(charts.get('THREEBETTER_VS_4BET') or {}).items()}
    default_threebet_response = next(iter(threebettor_vs_4bet.values()), {'5bet_jam': 'QQ+ AKs AKo', 'call': 'JJ-QQ AQs+ AKo'})
    for key in sorted(_final_valid_threebettor_vs_4bet_pairs()):
        if key not in threebettor_vs_4bet:
            threebettor_vs_4bet[key] = _final_copy_actions(default_threebet_response)
    charts['THREEBETTER_VS_4BET'] = {key: threebettor_vs_4bet[key] for key in sorted(threebettor_vs_4bet)}

    return charts


HERO_PREFLOP_CHARTS = _complete_profile(HERO_PREFLOP_CHARTS)
OPPONENT_PREFLOP_CHARTS = _complete_profile(OPPONENT_PREFLOP_CHARTS)

HERO_RFI_RAISE = HERO_PREFLOP_CHARTS['RFI_RAISE']
HERO_SB_FIRST_IN = HERO_PREFLOP_CHARTS['SB_FIRST_IN']
HERO_ISO_RAISE = HERO_PREFLOP_CHARTS['ISO_RAISE']
HERO_OVER_LIMP = HERO_PREFLOP_CHARTS['OVER_LIMP']
HERO_OPEN_LIMP = HERO_PREFLOP_CHARTS['OPEN_LIMP']
HERO_BB_VS_SB_LIMP = HERO_PREFLOP_CHARTS['BB_VS_SB_LIMP']
HERO_VS_OPEN = HERO_PREFLOP_CHARTS['VS_OPEN']
HERO_VS_OPEN_CALLERS = HERO_PREFLOP_CHARTS['VS_OPEN_CALLERS']
HERO_OPENER_VS_3BET = HERO_PREFLOP_CHARTS['OPENER_VS_3BET']
HERO_THREEBETTER_VS_4BET = HERO_PREFLOP_CHARTS['THREEBETTER_VS_4BET']
HERO_COLD_4BET = HERO_PREFLOP_CHARTS['COLD_4BET']
HERO_LIMPER_VS_ISO = HERO_PREFLOP_CHARTS['LIMPER_VS_ISO']

OPPONENT_RFI_RAISE = OPPONENT_PREFLOP_CHARTS['RFI_RAISE']
OPPONENT_SB_FIRST_IN = OPPONENT_PREFLOP_CHARTS['SB_FIRST_IN']
OPPONENT_ISO_RAISE = OPPONENT_PREFLOP_CHARTS['ISO_RAISE']
OPPONENT_OVER_LIMP = OPPONENT_PREFLOP_CHARTS['OVER_LIMP']
OPPONENT_OPEN_LIMP = OPPONENT_PREFLOP_CHARTS['OPEN_LIMP']
OPPONENT_BB_VS_SB_LIMP = OPPONENT_PREFLOP_CHARTS['BB_VS_SB_LIMP']
OPPONENT_VS_OPEN = OPPONENT_PREFLOP_CHARTS['VS_OPEN']
OPPONENT_VS_OPEN_CALLERS = OPPONENT_PREFLOP_CHARTS['VS_OPEN_CALLERS']
OPPONENT_OPENER_VS_3BET = OPPONENT_PREFLOP_CHARTS['OPENER_VS_3BET']
OPPONENT_THREEBETTER_VS_4BET = OPPONENT_PREFLOP_CHARTS['THREEBETTER_VS_4BET']
OPPONENT_COLD_4BET = OPPONENT_PREFLOP_CHARTS['COLD_4BET']
OPPONENT_LIMPER_VS_ISO = OPPONENT_PREFLOP_CHARTS['LIMPER_VS_ISO']

RFI_RAISE = OPPONENT_RFI_RAISE
OPEN_LIMP = OPPONENT_OPEN_LIMP
SB_FIRST_IN = OPPONENT_SB_FIRST_IN
ISO_RAISE = OPPONENT_ISO_RAISE
OVER_LIMP = OPPONENT_OVER_LIMP
BB_VS_SB_LIMP = OPPONENT_BB_VS_SB_LIMP
VS_OPEN = OPPONENT_VS_OPEN
VS_OPEN_CALLERS = OPPONENT_VS_OPEN_CALLERS
OPENER_VS_3BET = OPPONENT_OPENER_VS_3BET
THREEBETTER_VS_4BET = OPPONENT_THREEBETTER_VS_4BET
COLD_4BET = OPPONENT_COLD_4BET
LIMPER_VS_ISO = OPPONENT_LIMPER_VS_ISO

RANGE_PROFILES['hero'] = HERO_PREFLOP_CHARTS
RANGE_PROFILES['opponent'] = OPPONENT_PREFLOP_CHARTS
RANGE_PROFILES['villain'] = OPPONENT_PREFLOP_CHARTS
