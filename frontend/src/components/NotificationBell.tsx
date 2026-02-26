import React, { useState, useEffect } from 'react';
import { Dropdown, List, Button, Empty, Spin, Tag } from 'antd';
import { Bell } from 'lucide-react';
import { CheckOutlined } from '@ant-design/icons';
import { announcementApi } from '../services/api';
import ReactMarkdown from 'react-markdown';

interface Announcement {
  id: string;
  title: string;
  content: string;
  priority: string;
  type: string;
  published_at: string;
  is_read: boolean;
  read_at: string | null;
}

const NotificationBell: React.FC = () => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(false);
  const [dropdownVisible, setDropdownVisible] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // 加载未读数量
  const loadUnreadCount = async () => {
    try {
      const response = await announcementApi.user.getUnreadCount();
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('加载未读数量失败:', error);
    }
  };

  // 加载通知列表
  const loadAnnouncements = async () => {
    setLoading(true);
    try {
      const response = await announcementApi.user.getAnnouncements({
        page: 1,
        page_size: 10,
      });
      setAnnouncements(response.data.items);
    } catch (error) {
      console.error('加载通知列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 标记为已读
  const markAsRead = async (id: string) => {
    try {
      await announcementApi.user.markAsRead(id);
      // 更新本地状态
      setAnnouncements(prev =>
        prev.map(item =>
          item.id === id ? { ...item, is_read: true, read_at: new Date().toISOString() } : item
        )
      );
      setUnreadCount(prev => Math.max(0, prev - 1));
    } catch (error) {
      console.error('标记已读失败:', error);
    }
  };

  // 展开/收起通知详情
  const toggleExpand = (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
    } else {
      setExpandedId(id);
      // 展开时标记为已读
      const announcement = announcements.find(item => item.id === id);
      if (announcement && !announcement.is_read) {
        markAsRead(id);
      }
    }
  };

  // 轮询未读数量（每30秒）
  useEffect(() => {
    loadUnreadCount();
    const interval = setInterval(loadUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  // 打开下拉菜单时加载通知列表
  useEffect(() => {
    if (dropdownVisible) {
      loadAnnouncements();
    }
  }, [dropdownVisible]);

  // 优先级颜色
  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'red';
      case 'warning':
        return 'orange';
      case 'info':
      default:
        return 'blue';
    }
  };

  // 类型图标
  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'system':
        return '⚙️';
      case 'maintenance':
        return '🔧';
      case 'feature':
        return '✨';
      case 'event':
        return '📅';
      default:
        return '📢';
    }
  };

  const dropdownContent = (
    <div className="w-96 bg-gray-800 rounded-lg shadow-xl border border-gray-700">
      <div className="p-4 border-b border-gray-700 flex justify-between items-center">
        <h3 className="text-white font-semibold">通知中心</h3>
        {unreadCount > 0 && (
          <Tag color="blue">{unreadCount} 条未读</Tag>
        )}
      </div>

      <div className="max-h-96 overflow-y-auto">
        {loading ? (
          <div className="flex justify-center items-center py-12">
            <Spin />
          </div>
        ) : announcements.length === 0 ? (
          <Empty
            description="暂无通知"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            className="py-12"
          />
        ) : (
          <List
            dataSource={announcements}
            renderItem={(item) => (
              <div
                key={item.id}
                className={`p-4 border-b border-gray-700 cursor-pointer hover:bg-gray-750 transition-colors ${
                  !item.is_read ? 'bg-gray-750/50' : ''
                }`}
                onClick={() => toggleExpand(item.id)}
              >
                <div className="flex items-start gap-3">
                  {/* 未读标识 */}
                  {!item.is_read && (
                    <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0" />
                  )}

                  <div className="flex-1 min-w-0">
                    {/* 标题行 */}
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{getTypeIcon(item.type)}</span>
                      <span className="text-white font-medium truncate flex-1">
                        {item.title}
                      </span>
                      <Tag color={getPriorityColor(item.priority)} className="flex-shrink-0">
                        {item.priority === 'urgent' && '紧急'}
                        {item.priority === 'warning' && '警告'}
                        {item.priority === 'info' && '普通'}
                      </Tag>
                    </div>

                    {/* 时间 */}
                    <div className="text-xs text-gray-400 mb-2">
                      {new Date(item.published_at).toLocaleString('zh-CN')}
                    </div>

                    {/* 内容预览/完整内容 */}
                    {expandedId === item.id ? (
                      <div className="text-sm text-gray-300 prose prose-invert prose-sm max-w-none">
                        <ReactMarkdown>{item.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <div className="text-sm text-gray-400 line-clamp-2">
                        {item.content}
                      </div>
                    )}

                    {/* 已读标识 */}
                    {item.is_read && (
                      <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
                        <CheckOutlined />
                        <span>已读</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          />
        )}
      </div>

      {announcements.length > 0 && (
        <div className="p-3 border-t border-gray-700 text-center">
          <Button
            type="link"
            size="small"
            onClick={() => {
              setDropdownVisible(false);
              // TODO: 跳转到通知中心页面
              // window.location.href = '/notifications';
            }}
          >
            查看全部
          </Button>
        </div>
      )}
    </div>
  );

  return (
    <Dropdown
      overlay={dropdownContent}
      trigger={['click']}
      open={dropdownVisible}
      onOpenChange={setDropdownVisible}
      placement="bottomRight"
    >
      <button className="h-10 px-3 bg-slate-900/50 rounded-full flex items-center justify-center cursor-pointer hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all text-slate-400 hover:text-white relative">
        <Bell size={19} />
        {unreadCount > 0 && (
          <span className="absolute top-2.5 right-3 w-2 h-2 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.6)] ring-1 ring-slate-900" />
        )}
      </button>
    </Dropdown>
  );
};

export default NotificationBell;
