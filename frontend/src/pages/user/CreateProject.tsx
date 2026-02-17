import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Steps, Form, Input, Select, Button, Upload, message, Typography, Divider, Tooltip, Space, Tag } from 'antd';
import { InboxOutlined, LeftOutlined, InfoCircleOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import { projectApi } from '../../services/api';
import QuotaLimitModal from '../../components/modals/QuotaLimitModal';

const { Dragger } = Upload;
const { Title, Paragraph } = Typography;
const { Option } = Select;

interface SplitRuleOption {
  id: string;
  name: string;
  display_name: string;
  pattern_type: string;
  example?: string;
  is_default: boolean;
}

const CreateProject: React.FC = () => {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [form] = Form.useForm();
  const [showQuotaModal, setShowQuotaModal] = useState(false);
  const [splitRules, setSplitRules] = useState<SplitRuleOption[]>([]);
  const [loadingRules, setLoadingRules] = useState(false);

  // 获取拆分规则列表
  useEffect(() => {
    const fetchSplitRules = async () => {
      setLoadingRules(true);
      try {
        const response = await projectApi.getSplitRuleOptions();
        setSplitRules(response.data);
      } catch (error) {
        console.error('获取拆分规则失败:', error);
        // 使用默认规则作为后备
        setSplitRules([
          { id: '1', name: 'standard_chinese', display_name: '中文标准 - 第N章', pattern_type: 'regex', is_default: true },
          { id: '2', name: 'blank_line', display_name: '空行分隔', pattern_type: 'blank_line', is_default: false },
        ]);
      } finally {
        setLoadingRules(false);
      }
    };
    fetchSplitRules();
  }, []);

  const novelTypes = ['都市', '古装', '科幻', '玄幻', '武侠', '言情', '悬疑', '其他'];

  const onFinish = async (values: any) => {
    if (fileList.length === 0) {
      message.error('请上传小说文件');
      return;
    }

    setLoading(true);
    try {
      // 处理拆分规则：将规则ID转换为规则对象
      const { split_rule_id, ...rest } = values;
      const projectData = {
        ...rest,
        // 如果选择了拆分规则，传递规则ID
        ...(split_rule_id && { split_rule_id }),
      };

      // 1. 使用封装的 API 创建项目
      const projectResponse = await projectApi.createProject(projectData);
      const project = projectResponse.data;

      // 2. 上传文件
      await projectApi.uploadFile(
        project.id,
        fileList[0].originFileObj as File
      );

      message.success('项目创建成功！');
      navigate('/dashboard');
    } catch (error: any) {
      // 检查是否是配额限制错误
      const errorDetail = error.response?.data?.detail || '';

      if (error.response?.status === 403 && (errorDetail.includes('积分') || errorDetail.includes('配额'))) {
        // 积分不足，显示升级引导弹窗
        setShowQuotaModal(true);
      } else if (errorDetail.includes('未识别到任何章节') || errorDetail.includes('拆分规则')) {
        // 拆分失败，显示友好提示
        const lines = errorDetail.split('\n').filter((l: string) => l.trim());
        const friendlyMessage = lines[0] || '章节拆分失败';
        message.error({
          content: (
            <div>
              <div>{friendlyMessage}</div>
              <div className="text-xs text-gray-400 mt-1">
                建议：尝试选择「空行分隔」或「双换行分隔」规则
              </div>
            </div>
          ),
          duration: 5,
        });
      } else {
        // 其他错误，显示具体错误信息
        const errorMessage = errorDetail || error.message || '操作失败，请稍后重试';
        message.error(errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    {
      title: '填写信息',
      description: '设定项目基本参数',
    },
    {
      title: '上传文件',
      description: '支持 TXT, DOCX, PDF',
    },
    {
      title: '完成创建',
      description: '开始AI处理流程',
    },
  ];

  return (
    <>
      {/* 积分不足弹窗 */}
      <QuotaLimitModal
        isOpen={showQuotaModal}
        onClose={() => setShowQuotaModal(false)}
        currentTier="FREE"
        currentBalance={0}
        requiredCredits={100}
        taskType="创建项目"
      />

      {/* 原有的创建项目页面 */}
      <div style={{ maxWidth: 800, margin: '0 auto' }}>
        <div style={{ marginBottom: 24 }}>
          <Button icon={<LeftOutlined />} type="text" onClick={() => navigate('/dashboard')}>
            返回工作台
          </Button>
        </div>

        <Card bordered={false}>
          <div style={{ textAlign: 'center', marginBottom: 40 }}>
            <Title level={2}>开始你的剧本改编</Title>
            <Paragraph type="secondary">
              只需简单几步，AI 将协助你将小说转化为专业剧本
            </Paragraph>
          </div>

          <Steps current={currentStep} items={steps} style={{ marginBottom: 40 }} />

          <Form
            form={form}
            layout="vertical"
            onFinish={onFinish}
            initialValues={{
              novel_type: '都市',
              batch_size: 5,
              chapter_split_rule: 'auto'
            }}
          >
            {/* Step 1: Basic Info */}
            <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
              <Form.Item
                name="name"
                label="项目名称"
                rules={[{ required: true, message: '请输入项目名称' }]}
              >
                <Input placeholder="给你的剧本起个名字，例如：星际迷航改编版" size="large" />
              </Form.Item>

              <Form.Item
                name="novel_type"
                label="小说类型"
                rules={[{ required: true }]}
              >
                <Select size="large">
                  {novelTypes.map(type => (
                    <Option key={type} value={type}>{type}</Option>
                  ))}
                </Select>
              </Form.Item>

              <Form.Item name="description" label="项目描述">
                <Input.TextArea rows={4} placeholder="简要描述故事梗概或改编方向（可选）" />
              </Form.Item>

              <Form.Item label="高级设置" style={{ marginBottom: 0 }}>
                <Form.Item
                  name="batch_size"
                  label="处理批次大小 (章)"
                  tooltip="建议5-10章，AI处理效果最佳"
                  style={{ display: 'inline-block', width: 'calc(50% - 8px)', marginRight: 16 }}
                >
                  <Input type="number" min={1} max={20} />
                </Form.Item>
                <Form.Item
                  name="split_rule_id"
                  label={
                    <span>
                      章节拆分规则 <Tooltip title="选择如何识别和拆分小说章节"><InfoCircleOutlined /></Tooltip>
                    </span>
                  }
                  style={{ display: 'inline-block', width: 'calc(50% - 8px)' }}
                >
                  <Select
                    placeholder="选择章节拆分规则"
                    loading={loadingRules}
                  >
                    {splitRules.map(rule => (
                      <Option key={rule.id} value={rule.id}>
                        <Space>
                          {rule.display_name}
                          {rule.is_default && <Tag color="blue">默认</Tag>}
                        </Space>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Form.Item>

              <Divider />
              <div style={{ textAlign: 'right' }}>
                <Button type="primary" onClick={() => setCurrentStep(1)} size="large">
                  下一步：上传文件
                </Button>
              </div>
            </div>

            {/* Step 2: Upload */}
            <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
              <Form.Item label="上传小说原稿">
                <Dragger
                  accept=".txt,.docx,.pdf"
                  beforeUpload={(file) => {
                    setFileList([file]);
                    return false;
                  }}
                  fileList={fileList}
                  onRemove={() => setFileList([])}
                  style={{ padding: 40 }}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined style={{ color: '#1677ff' }} />
                  </p>
                  <p className="ant-upload-text">点击或将文件拖拽到这里上传</p>
                  <p className="ant-upload-hint">
                    支持 TXT, DOCX, PDF 格式，最大支持 50MB
                  </p>
                </Dragger>
              </Form.Item>

              <Divider />
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Button onClick={() => setCurrentStep(0)} size="large">
                  上一步
                </Button>
                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  loading={loading}
                  disabled={fileList.length === 0}
                >
                  创建项目
                </Button>
              </div>
            </div>
          </Form>
        </Card>
      </div>
    </>
  );
};

export default CreateProject;
