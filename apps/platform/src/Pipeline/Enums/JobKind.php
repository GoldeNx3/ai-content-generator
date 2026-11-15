<?php

namespace Modules\Pipeline\Enums;

enum JobKind: string
{
    case Classify = 'classify';
    case Research = 'research';
    case Write = 'write';
    case QaArticle = 'qa_article';
    case AutoFixArticle = 'auto_fix_article';
    case PrepareWordPress = 'prepare_wordpress';
    case PublishWordPress = 'publish_wordpress';
    case LearnFeedback = 'learn_feedback';

    public function isPaid(): bool
    {
        return $this !== self::PublishWordPress;
    }

    public function requiresOpenAi(): bool
    {
        return ! in_array($this, [self::PublishWordPress, self::PrepareWordPress], true);
    }
}
