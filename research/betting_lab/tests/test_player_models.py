import unittest
from datetime import datetime,timedelta,timezone
from dataclasses import replace
from betlab.player_models import PlayerGame,build_prior_examples,team_td_opportunity_probability,td_chronological_experiment,yards_chronological_experiment

class PlayerModels(unittest.TestCase):
    def test_prior_only(self):
        a=PlayerGame('p','a',2023,1,'2023-09-10T17:00:00Z','2023-09-10T23:00:00Z',5,2,1,1,.7,60,10,1)
        b=replace(a,game_id='b',week=2,kickoff_utc='2023-09-17T17:00:00Z',result_published_utc='2023-09-17T23:00:00Z',targets=100,touchdowns=0)
        out=build_prior_examples([b,a])
        self.assertEqual(out[0]['features']['prior_games'],0)
        self.assertEqual(out[1]['features']['targets_4'],5)
        self.assertEqual(out[1]['td_label'],0)
    def test_source_time_reject(self):
        a=PlayerGame('p','a',2023,1,'2023-09-10T17:00:00Z','2023-09-10T16:00:00Z',5,2,1,1,.7,60,10,1)
        with self.assertRaises(ValueError):build_prior_examples([a])
    def test_team_probability(self):
        self.assertAlmostEqual(team_td_opportunity_probability(0,.2),0)
        self.assertGreater(team_td_opportunity_probability(3,.2),team_td_opportunity_probability(2,.2))
    def test_experiments_smoke_synthetic(self):
        rows=[]
        for season in (2023,2024,2025):
            for i in range(65):
                # Explicitly SYNTHETIC labels. Tests assert runnable model selection, not real performance.
                d=datetime(season,9,1,tzinfo=timezone.utc)+timedelta(days=i)
                r=PlayerGame(f'p{i%12}',f'{season}_{i}',season,(i%18)+1,d.isoformat(),(d+timedelta(hours=8)).isoformat(),
                 i%8,(i*3)%12,i%3,i%2,0.2+.05*(i%10),i%90,(i*7)%85,int(i%4==0),
                 team_expected_tds=2.5,team_expected_tds_observed_utc=(d-timedelta(hours=1)).isoformat())
                rows.append(r)
        features=build_prior_examples(rows)
        td=td_chronological_experiment(features)
        yards=yards_chronological_experiment(features)
        self.assertEqual(td['holdout_n'],65)
        self.assertEqual(yards['holdout_n'],65)
        self.assertEqual(td['status'],'EXPERIMENTAL_NOT_PROVEN')
if __name__=='__main__':unittest.main()