from django.test import SimpleTestCase, TestCase
from .group_statistics import top_rental_groups


class GroupRankingTests(SimpleTestCase):
    def row(self, group='TEST-A', days=3, month=1, supplier_id=1):
        return dict(group=group,group_key=group,days=days,month=month,supplier_id=supplier_id,supplier='TEST-FIRM-'+str(supplier_id))

    def test_ranking_uses_days_not_booking_count_and_seasons_sum_to_total(self):
        rows, missing=top_rental_groups([self.row(days=2),self.row(days=2,month=8),self.row(group='TEST-B',days=10,month=3)])
        self.assertEqual([r['days'] for r in rows],[10,4])
        self.assertEqual(rows[1]['winter'],2)
        self.assertEqual(rows[1]['summer'],2)
        self.assertEqual(missing,0)
        for row in rows:self.assertEqual(sum(row[k] for k in ['winter','spring','summer','autumn']),row['days'])

    def test_same_group_names_at_different_suppliers_are_separate(self):
        rows,_=top_rental_groups([self.row(),self.row(supplier_id=2)])
        self.assertEqual(len(rows),2)

    def test_top_ten_and_missing_records(self):
        rows,missing=top_rental_groups([self.row(group=str(i),days=i+1) for i in range(12)]+[self.row(group=''),self.row(days=0)])
        self.assertEqual(len(rows),10)
        self.assertEqual(rows[0]['days'],12)
        self.assertEqual(missing,2)

    def test_each_month_has_one_calendar_season(self):
        rows,_=top_rental_groups([self.row(days=1,month=m) for m in range(1,13)])
        for key in ['winter','spring','summer','autumn']:self.assertEqual(rows[0][key],3)


class GroupRankingPageTests(TestCase):
    def test_statistics_ranking_respects_year_and_excludes_cancelled(self):
        from . import test_future_statistics as data
        from suppliers.models import VehicleGroup
        data.FutureStatisticsTests.setUp(self)
        group=VehicleGroup.objects.create(supplier=self.first,group_code='TEST-GROUP',group_name='TEST-CLASS')
        data.FutureStatisticsTests.booking(self,vehicle_group=group,rental_days=3)
        data.FutureStatisticsTests.booking(self,vehicle_group=group,rental_days=90,status='CANCELLED')
        response=self.client.get(self.url,{'year':2027})
        row,=response.context['top_groups']
        self.assertEqual(row['days'],3)
        self.assertEqual(row['winter'],3)
        self.assertContains(response,'TEST-CLASS (TEST-GROUP)')
        self.assertEqual(self.client.get(self.url,{'year':2026}).context['top_groups'],[])
