# Copyright 2020 Adam Wildavsky and the Bridge Hackathon contributors
#
#   Use of this source code is governed by an MIT-style
#   license that can be found in the LICENSE file or at
#   https://opensource.org/licenses/MIT

# To run the tests from the command line:
# cd DDS
# python3 -m unittest discover

import json
import os
import unittest

from test.utilities import nesw_to_dds_format
from test.utilities import rotate_nesw_to_eswn
from test.utilities import run_in_threads
from test.utilities import check_dd_table_results

from src.dds import DDS
import logging
import sys

# So we can use multi-line strings as comments:
# pylint: disable=pointless-string-statement

logger = logging.getLogger()
logger.level = logging.DEBUG
stream_handler = logging.StreamHandler(sys.stdout)
logger.addHandler(stream_handler)


class TestDDS(unittest.TestCase):
    """
    Tests DDS output for a few specific deals.

    TODO:   Test for different values of max_threads.
            Tweak input by exchanging an A and a K, make sure output changes to match.
    """

    def setUp(self):
        # We do this here rather than in setUpClass() in order to test
        # multiple serial instantiations of DDS. At one point DDS had
        # a bug that caused it to crash when we did this.
        self.dds = DDS()

    def test_one_sample_deal(self):
        """
        Solve a sample.
            S AQ85
            H AK976
            D 5
            C J87

        S K643      JT
        H T8        QJ5432
        D AK742     Q9
        C T5        KQ9

            S 972
            H
            D JT863
            C A6432
        """

        with open(os.path.join('data', 'sample_deal.json')) as file:
            deal = json.load(file)

        dds_table = self.dds.dd_table(deal["hands"])
        formatted_dds_table = self.dds.format_dd_table(dds_table)

        self.assertEqual(8, formatted_dds_table['C']['S'],
                         'South can take 8 tricks with clubs as trump')
        self.assertEqual(6, formatted_dds_table['N']['E'],
                         'East can take 6 tricks at notrump')

        dds_par = self.dds.par(dds_table, 1)

        self.assertEqual(110, dds_par['NS'], 'NS has 110')
        self.assertEqual(-110, dds_par['EW'], 'EW has -110')

        # logging.getLogger().info(
        #     '\n'.join([''.join(['{:4}'.format(item) for item in row]) for row in dds_par.parScore]))

    def test_ns_make_7_of_everything(self):
        """
        NS make 13 tricks in everything.
            S AKQJ
            H AKQJ
            D T98
            C T9

        S 76        5432
        H 876       5432
        D 7654      32
        C 8765      432

            S T98
            H T9
            D AKQJ
            C AKQJ
        """

        nesw = [
            "AKQJ.AKQJ.T98.T9",
            "5432.5432.32.432",
            "T98.T9.AKQJ.AKQJ",
            "76.876.7654.8765"
        ]

        hands = nesw_to_dds_format(nesw)

        dds_table = self.dds.dd_table(hands)
        formatted_dds_table = self.dds.format_dd_table(dds_table)

        for denomination in ['C', 'D', 'H', 'S', 'N']:
            for declarer in ['N', 'S']:
                self.assertEqual(13, formatted_dds_table[denomination][declarer],
                                 "NS can take 13 tricks in any denomination.")
            for declarer in ['E', 'W']:
                self.assertEqual(0, formatted_dds_table[denomination][declarer],
                                 "EW can take 0 tricks in any denomination.")

        # Now test the same deal, but rotated 90 degrees clockwise

        nesw = rotate_nesw_to_eswn(nesw)

        hands = nesw_to_dds_format(nesw)

        dds_table = self.dds.dd_table(hands)
        formatted_dds_table = self.dds.format_dd_table(dds_table)

        for denomination in ['C', 'D', 'H', 'S', 'N']:
            for declarer in ['N', 'S']:
                self.assertEqual(0, formatted_dds_table[denomination][declarer],
                                 "NS can take 0 tricks in any denomination.")
            for declarer in ['E', 'W']:
                self.assertEqual(13, formatted_dds_table[denomination][declarer],
                                 "EW can take 13 tricks in any denomination.")

    def test_everyone_makes_3n(self):
        """
        Everyone makes 9 tricks in notrump!
        See: https://bridge.thomasoandrews.com/deals/everybody/

            S QT9
            H A8765432
            D KJ
            C -

        S -         KJ
        H KJ        -
        D QT9       A8765432
        C A8765432  QT9

            S A8765432
            H QT9
            D -
            C KJ
        """

        nesw = [
            "QT9.A8765432.KJ.",
            "KJ..A8765432.QT9",
            "A8765432.QT9..KJ",
            ".KJ.QT9.A8765432"
        ]

        hands = nesw_to_dds_format(nesw)

        dds_table = self.dds.dd_table(hands)
        formatted_dds_table = self.dds.format_dd_table(dds_table)

        for declarer in ['N', 'E', 'S', 'W']:
            self.assertEqual(9, formatted_dds_table['N'][declarer],
                             "Every declarer can take 9 tricks at NT.")

    def skip_test_one_trick_deal(self):
        """
        This test fails. We have not yet implemented deals of
        fewer than 52 cards.

            S A
            H 
            D 
            C 

        S       
        H           A
        D      
        C A         

            S 
            H
            D A
            C 
        """

        nesw = [
            "A...",
            ".A..",
            "..A.",
            "...A"
        ]

        hands = nesw_to_dds_format(nesw)

        dds_table = self.dds.dd_table(hands)
        formatted_dds_table = self.dds.format_dd_table(dds_table)

        self.assertEqual(0, formatted_dds_table['S']['N'],
                         'South can take no tricks at notrump')
        self.assertEqual(1, formatted_dds_table['S']['N'],
                         'South can take one tricks at diamonds')

    def test_parallel_CalcDDTable(self):
        """
        Tests parallel access to dds.calc_dd_table.
        Cards are from libdds/hands/list100.txt

        PBN 0 0 4 2 "N:T742.QT6.AJ7.Q64 AQ83.A54.KQ9.T82 K65.J873.653.A97 J9.K92.T842.KJ53"
        FUT 10 3 2 2 1 1 1 3 3 0 0 14 3 6 3 8 11 7 9 6 13 0 0 32 0 128 0 0 0 32 0 5 5 5 5 5 5 5 5 4 4
        TABLE 5 8 5 8  6 7 6 7  4 8 4 8  4 8 4 8  5 8 5 8
        """

        nesw = [
            "T742.QT6.AJ7.Q64",
            "AQ83.A54.KQ9.T82",
            "K65.J873.653.A97",
            "J9.K92.T842.KJ53"
        ]

        result = dict(
            S=dict(N=5, E=8, S=5, W=8),
            H=dict(N=6, E=7, S=6, W=7),
            D=dict(N=4, E=8, S=4, W=8),
            C=dict(N=4, E=8, S=4, W=8),
            N=dict(N=5, E=8, S=5, W=8)
        )

        deal = nesw_to_dds_format(nesw)

        def calc_dd_table(deal):
            dds_table = self.dds.dd_table(deal)
            return self.dds.format_dd_table(dds_table)

        def test_fn(self, deal):
            for i in range(2):
                yield calc_dd_table(deal)

        solutions = run_in_threads(2, test_fn, args=(self, deal))

        check_dd_table_results(self, solutions, result)


if __name__ == '__main__':
    unittest.main()
