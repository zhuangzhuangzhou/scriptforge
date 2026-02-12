import React, { useState, useEffect } from 'react';
import { Form, InputNumber, Switch, Button, message, Spin, Card, Divider } from 'antd';
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons';
import { GlassCard } from '../../components/ui/GlassCard';
import api from '../../services/api';

interface SystemConfig {
  key: string;
  value: string;
  description: string;
  is_default: boolean;
}

const SystemSettings: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  const fetchConfigs = async () => {
    setLoading(true);
    try {
      const response = await api.get('/system/configs');
      const configs = response.data.configs as SystemConfig[];

      const values: Record<string, any> = {};
      configs.forEach(c => {
        if (c.key === 'token_billing_enabled') {
          values[c.key] = c.value === 'true';
        } else {
          values[c.key] = parseInt(c.value) || 0;
        }
      });
      form.setFieldsValue(values);
    } catch (error) {
      message.error('加载配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      const values = form.getFieldsValue();
      const configs: Record<string, string> = {};

      Object.entries(values).forEach(([key, value]) => {
        configs[key] = String(value);
      });

      await api.put('/system/configs', { configs });
      message.success('配置已保存');
    } catch (error) {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <GlassCard>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <h2 style={{ margin: 0, color: '#fff' }}>系统配置</h2>
          <div>
            <Button icon={<ReloadOutlined />} onClick={fetchConfigs} style={{ marginRight: 8 }}>
              刷新
            </Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
              保存
            </Button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
        ) : (
          <Form form={form} layout="vertical">
            <Card title="基础费用（每次任务固定收取）" size="small" style={{ marginBottom: 16, background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(51,65,85,0.5)' }} headStyle={{ color: '#fff', borderBottom: '1px solid rgba(51,65,85,0.5)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
                <Form.Item label="剧情拆解" name="credits_breakdown">
                  <InputNumber min={0} addonAfter="积分" style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="剧本生成" name="credits_script">
                  <InputNumber min={0} addonAfter="积分" style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="质检校验" name="credits_qa">
                  <InputNumber min={0} addonAfter="积分" style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="任务重试" name="credits_retry">
                  <InputNumber min={0} addonAfter="积分" style={{ width: '100%' }} />
                </Form.Item>
              </div>
            </Card>

            <Card title="Token 计费" size="small" style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(51,65,85,0.5)' }} headStyle={{ color: '#fff', borderBottom: '1px solid rgba(51,65,85,0.5)' }}>
              <Form.Item label="启用 Token 计费" name="token_billing_enabled" valuePropName="checked">
                <Switch checkedChildren="开" unCheckedChildren="关" />
              </Form.Item>
              <Divider style={{ borderColor: 'rgba(51,65,85,0.5)' }} />
              <p style={{ color: '#94a3b8', fontSize: 12, marginBottom: 16 }}>
                以下为默认 Token 价格，可在「模型管理 → 计费规则」中为每个模型单独设置
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
                <Form.Item label="输入 Token 价格" name="token_input_per_1k">
                  <InputNumber min={0} step={0.1} addonAfter="积分/1K" style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item label="输出 Token 价格" name="token_output_per_1k">
                  <InputNumber min={0} step={0.1} addonAfter="积分/1K" style={{ width: '100%' }} />
                </Form.Item>
              </div>
            </Card>
          </Form>
        )}
      </GlassCard>
    </div>
  );
};

export default SystemSettings;
