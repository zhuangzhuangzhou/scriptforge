import React, { useEffect, useState } from 'react';
import { Spin, Statistic, Row, Col, Progress, message } from 'antd';
import { UserOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { GlassModal } from '../../../components/ui/GlassModal';
import { announcementApi } from '../../../services/api';

interface AnnouncementStatsProps {
  visible: boolean;
  announcementId: string | null;
  onCancel: () => void;
}

interface Stats {
  announcement_id: string;
  read_count: number;
  total_users: number;
  read_rate: number;
}

const AnnouncementStats: React.FC<AnnouncementStatsProps> = ({
  visible,
  announcementId,
  onCancel,
}) => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    if (visible && announcementId) {
      loadStats();
    }
  }, [visible, announcementId]);

  const loadStats = async () => {
    if (!announcementId) return;

    setLoading(true);
    try {
      const response = await announcementApi.admin.getAnnouncementStats(announcementId);
      setStats(response.data);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '加载统计失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <GlassModal
      title="通知统计"
      open={visible}
      onCancel={onCancel}
      footer={null}
      width={600}
    >
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <Spin size="large" />
        </div>
      ) : stats ? (
        <div>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic
                title="已读人数"
                value={stats.read_count}
                prefix={<CheckCircleOutlined />}
                suffix="人"
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="总用户数"
                value={stats.total_users}
                prefix={<UserOutlined />}
                suffix="人"
              />
            </Col>
            <Col span={8}>
              <Statistic
                title="已读率"
                value={stats.read_rate}
                suffix="%"
              />
            </Col>
          </Row>

          <div className="mt-8">
            <div className="mb-2 text-gray-400">阅读进度</div>
            <Progress
              percent={stats.read_rate}
              status={stats.read_rate >= 80 ? 'success' : 'active'}
              strokeColor={{
                '0%': '#108ee9',
                '100%': '#87d068',
              }}
            />
          </div>

          <div className="mt-6 p-4 bg-gray-800 rounded">
            <div className="text-sm text-gray-400">
              <div className="mb-2">
                <span className="font-medium">未读人数：</span>
                <span className="text-white">{stats.total_users - stats.read_count} 人</span>
              </div>
              <div>
                <span className="font-medium">未读率：</span>
                <span className="text-white">{(100 - stats.read_rate).toFixed(2)}%</span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-400 py-12">
          暂无统计数据
        </div>
      )}
    </GlassModal>
  );
};

export default AnnouncementStats;
