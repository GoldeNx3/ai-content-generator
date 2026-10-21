<?php

namespace Modules\WordPress\Commands;

use Carbon\CarbonImmutable;
use Modules\WordPress\Models\WordPressAuthRequest;

final class CreateAuthRequestCommand
{
    public function execute(string $stateHash, int $workspaceId, int $userId, string $siteUrl, ?string $apiUrl, CarbonImmutable $expiresAt): void
    {
        WordPressAuthRequest::query()->where('expires_at', '<', CarbonImmutable::now())->delete();
        WordPressAuthRequest::query()->create([
            'state_hash' => $stateHash, 'workspace_id' => $workspaceId, 'user_id' => $userId,
            'site_url' => $siteUrl, 'api_url' => $apiUrl, 'expires_at' => $expiresAt,
        ]);
    }
}
