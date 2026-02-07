import React, { useState, useEffect } from 'react';
import { Layout, Button, Space, Modal, Tag, message } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import SkillsEditor from '../../components/SkillsEditor';
import { GlassCard } from '../../components/ui/GlassCard';
import { GlassTable } from '../../components/ui/GlassTable';

const { Content } = Layout;

interface Skill {
  id: string;
  name: string;
  display_name: string;
  description: string;
  category: string;
  is_builtin: boolean;
  updated_at: string;
}

const SkillsManagement: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [showEditor, setShowEditor] = useState(false);

  useEffect(() => {
    loadSkills();
  }, []);

  const loadSkills = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/skills/available', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      if (!response.ok) throw new Error('加载失败');
      const data = await response.json();
      setSkills(data.skills || []);
    } catch (error) {
      message.error('加载Skills失败');
    } finally {
      setLoading(false);
    }
  };

  const handleEditSkill = (skill: Skill) => {
    setSelectedSkill(skill);
    setShowEditor(true);
  };

  const handleDeleteSkill = async (skillId: string) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个Skill吗？此操作不可恢复。',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/admin/skills/${skillId}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });
          if (!response.ok) throw new Error('删除失败');
          message.success('删除成功');
          loadSkills();
        } catch (error) {
          message.error('删除失败');
        }
      }
    });
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: Skill) => (
        <Space direction="vertical" size={0}>
          <span className="font-medium">{text}</span>
          <span className="text-gray-400 text-xs">{record.name}</span>
        </Space>
      )
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (
        <Tag color={category === 'breakdown' ? 'blue' : 'green'}>
          {category === 'breakdown' ? '剧情拆解' : '剧本生成'}
        </Tag>
      )
    },
    {
      title: '类型',
      dataIndex: 'is_builtin',
      key: 'is_builtin',
      render: (isBuiltin: boolean) => (
        <Tag color={isBuiltin ? 'gold' : 'default'}>
          {isBuiltin ? '内置' : '自定义'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Skill) => (
        <Space>
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEditSkill(record)}
          >
            编辑代码
          </Button>
          {!record.is_builtin && (
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteSkill(record.id)}
            >
              删除
            </Button>
          )}
        </Space>
      )
    }
  ];

  if (showEditor && selectedSkill) {
    return (
      <SkillsEditor
        skillId={selectedSkill.id}
        skillName={selectedSkill.display_name}
      />
    );
  }

  return (
    <Layout className="bg-transparent min-h-screen">
      <Content style={{ padding: '24px' }}>
        <GlassCard>
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-semibold text-white m-0">Skills管理</h2>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              className="bg-blue-600 border-none hover:bg-blue-500"
            >
              创建自定义Skill
            </Button>
          </div>
          <GlassTable
            dataSource={skills}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 10 }}
          />
        </GlassCard>

        {/* Skill开发指南 */}
        <GlassCard className="mt-6">
          <h2 className="text-xl font-semibold text-white mb-6">Skill开发指南</h2>
          <div className="text-slate-300 space-y-6">
            <div>
              <h4 className="text-lg font-medium text-blue-400 mb-2">什么是Skill？</h4>
              <p>
                Skill是剧本生成流水线中的基本处理单元。每个Skill负责一个特定的任务，
                如提取冲突点、识别剧情钩子、编写对话等。
              </p>
            </div>

            <div>
              <h4 className="text-lg font-medium text-blue-400 mb-2">内置Skills</h4>
              <ul className="list-disc list-inside space-y-1 ml-4">
                <li><strong className="text-white">冲突点提取</strong> - 从章节中提取冲突点</li>
                <li><strong className="text-white">剧情钩子识别</strong> - 识别吸引观众的悬念和转折</li>
                <li><strong className="text-white">人物分析</strong> - 分析人物关系和性格</li>
                <li><strong className="text-white">场景识别</strong> - 识别场景信息</li>
                <li><strong className="text-white">情绪提取</strong> - 提取情绪变化点</li>
                <li><strong className="text-white">剧集规划</strong> - 规划剧集结构</li>
              </ul>
            </div>

            <div>
              <h4 className="text-lg font-medium text-blue-400 mb-2">自定义Skills</h4>
              <p>
                您可以创建自定义Skills来扩展系统功能。自定义Skills可以复制内置Skills
                进行修改，或者从零开始编写。
              </p>
            </div>
          </div>
        </GlassCard>
      </Content>
    </Layout>
  );
};

export default SkillsManagement;
