import React, { useEffect } from 'react';
import { Form, message } from 'antd';
import { GlassModal } from '../../../components/ui/GlassModal';
import { GlassInput } from '../../../components/ui/GlassInput';
import { GlassSelect } from '../../../components/ui/GlassSelect';
import { GlassDatePicker } from '../../../components/ui/GlassDatePicker';
import { announcementApi } from '../../../services/api';
import dayjs from 'dayjs';

const { TextArea } = GlassInput;

interface AnnouncementModalProps {
  visible: boolean;
  announcement: any | null;
  onCancel: () => void;
  onSuccess: () => void;
}

const AnnouncementModal: React.FC<AnnouncementModalProps> = ({
  visible,
  announcement,
  onCancel,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = React.useState(false);

  useEffect(() => {
    if (visible) {
      if (announcement) {
        // 编辑模式：填充表单
        form.setFieldsValue({
          title: announcement.title,
          content: announcement.content,
          priority: announcement.priority,
          type: announcement.type,
          expires_at: announcement.expires_at ? dayjs(announcement.expires_at) : null,
        });
      } else {
        // 创建模式：重置表单
        form.resetFields();
      }
    }
  }, [visible, announcement, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const data = {
        title: values.title,
        content: values.content,
        priority: values.priority,
        type: values.type,
        expires_at: values.expires_at ? values.expires_at.toISOString() : undefined,
      };

      if (announcement) {
        // 更新
        await announcementApi.admin.updateAnnouncement(announcement.id, data);
        message.success('更新成功');
      } else {
        // 创建
        await announcementApi.admin.createAnnouncement(data);
        message.success('创建成功');
      }

      onSuccess();
    } catch (error: any) {
      if (error.errorFields) {
        // 表单验证错误
        return;
      }
      message.error(error.response?.data?.detail || '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <GlassModal
      title={announcement ? '编辑通知' : '创建通知'}
      open={visible}
      onCancel={onCancel}
      onOk={handleSubmit}
      confirmLoading={loading}
      width={700}
      okText="保存"
      cancelText="取消"
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          priority: 'info',
          type: 'system',
        }}
      >
        <Form.Item
          name="title"
          label="标题"
          rules={[
            { required: true, message: '请输入标题' },
            { max: 255, message: '标题不能超过255个字符' },
          ]}
        >
          <GlassInput placeholder="请输入通知标题" />
        </Form.Item>

        <Form.Item
          name="content"
          label="内容"
          rules={[{ required: true, message: '请输入内容' }]}
          extra="支持 Markdown 格式"
        >
          <TextArea
            rows={8}
            placeholder="请输入通知内容，支持 Markdown 格式"
          />
        </Form.Item>

        <div className="grid grid-cols-2 gap-4">
          <Form.Item
            name="type"
            label="类型"
            rules={[{ required: true, message: '请选择类型' }]}
          >
            <GlassSelect
              placeholder="请选择类型"
              options={[
                { value: 'system', label: '系统通知' },
                { value: 'maintenance', label: '维护公告' },
                { value: 'feature', label: '新功能' },
                { value: 'event', label: '活动' },
              ]}
            />
          </Form.Item>

          <Form.Item
            name="priority"
            label="优先级"
            rules={[{ required: true, message: '请选择优先级' }]}
          >
            <GlassSelect
              placeholder="请选择优先级"
              options={[
                { value: 'info', label: '普通' },
                { value: 'warning', label: '警告' },
                { value: 'urgent', label: '紧急' },
              ]}
            />
          </Form.Item>
        </div>

        <Form.Item
          name="expires_at"
          label="过期时间"
          extra="留空表示永久有效"
        >
          <GlassDatePicker
            showTime
            format="YYYY-MM-DD HH:mm:ss"
            placeholder="选择过期时间"
            style={{ width: '100%' }}
          />
        </Form.Item>
      </Form>
    </GlassModal>
  );
};

export default AnnouncementModal;
