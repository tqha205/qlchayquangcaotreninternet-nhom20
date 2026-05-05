"""
tests/test_campaign_model.py
============================
Unit tests cho CampaignModel - kiểm tra logic tính toán hiệu quả.
Không cần kết nối DB thật (test logic thuần Python).
"""

import pytest
from unittest.mock import patch, MagicMock
from app.models.campaign import CampaignModel


class TestGetEfficiencyStats:
    """Kiểm tra logic tính chỉ số hiệu quả chiến dịch."""

    def _make_campaign(self, budget, spent):
        return {'id': 1, 'name': 'Test', 'budget': budget, 'spent': spent, 'customer_name': 'KH'}

    @patch.object(CampaignModel, 'get_by_id')
    def test_returns_none_when_campaign_not_found(self, mock_get):
        mock_get.return_value = None
        result = CampaignModel.get_efficiency_stats(99)
        assert result is None

    @patch.object(CampaignModel, 'get_by_id')
    def test_good_label_when_spent_under_80_percent(self, mock_get):
        mock_get.return_value = self._make_campaign(budget=1_000_000, spent=700_000)
        result = CampaignModel.get_efficiency_stats(1)
        assert result['label'] == 'Tốt'
        assert result['spent_ratio'] == 70.0

    @patch.object(CampaignModel, 'get_by_id')
    def test_warning_label_when_spent_above_90_percent(self, mock_get):
        mock_get.return_value = self._make_campaign(budget=1_000_000, spent=950_000)
        result = CampaignModel.get_efficiency_stats(1)
        assert result['label'] == 'Cảnh báo'
        assert result['spent_ratio'] == 95.0

    @patch.object(CampaignModel, 'get_by_id')
    def test_zero_budget_does_not_raise(self, mock_get):
        mock_get.return_value = self._make_campaign(budget=0, spent=0)
        result = CampaignModel.get_efficiency_stats(1)
        assert result is not None
        assert result['spent_ratio'] == 0.0

    @patch.object(CampaignModel, 'get_by_id')
    def test_clicks_and_impressions_positive(self, mock_get):
        mock_get.return_value = self._make_campaign(budget=1_000_000, spent=500_000)
        result = CampaignModel.get_efficiency_stats(1)
        assert result['clicks'] > 0
        assert result['impressions'] > 0
        assert result['ctr'] > 0
