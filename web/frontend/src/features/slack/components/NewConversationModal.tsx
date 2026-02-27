import { type FC, useState } from 'react';
import { Button } from '../../../components/ui';
import { Modal } from '../../../components/ui';
import { Input } from '../../../components/ui';
import { useCreateConversation } from '../hooks';
import { ConversationStyle } from '../../../shared/constants';
import { generateId } from '../../../shared/utils';

interface NewConversationModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NewConversationModal: FC<NewConversationModalProps> = ({
  isOpen,
  onClose,
}) => {
  const createMutation = useCreateConversation();
  const [name, setName] = useState('');

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!name.trim()) return;

    const id = generateId('conv');

    try {
      await createMutation.mutateAsync({
        id,
        name: name.trim(),
        style: ConversationStyle.CASUAL,
      });
      handleClose();
    } catch {
      // Error handled in mutation
    }
  };

  const handleClose = () => {
    if (!createMutation.isPending) {
      setName('');
      onClose();
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="新建对话" size="sm">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="联系人名称"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="例如: Tom, Sarah, 产品组"
          autoFocus
        />

        <p className="text-xs text-text-muted">
          对话将自动保存，默认使用轻松随意的沟通风格
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="secondary"
            onClick={handleClose}
            disabled={createMutation.isPending}
          >
            取消
          </Button>
          <Button 
            type="submit" 
            variant="primary" 
            isLoading={createMutation.isPending}
            disabled={!name.trim()}
          >
            创建
          </Button>
        </div>
      </form>
    </Modal>
  );
};
