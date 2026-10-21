<?php

namespace Modules\WordPress\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\WordPress\Models\WordPressAuthRequest;

final class AuthRequestCommand
{
    public function create(string $stateHash, int $workspaceId, int $userId, string $siteUrl, ?string $apiUrl, CarbonImmutable $expiresAt): void
    {
        WordPressAuthRequest::query()->where('expires_at', '<', CarbonImmutable::now())->delete();
        WordPressAuthRequest::query()->create([
            'state_hash' => $stateHash, 'workspace_id' => $workspaceId, 'user_id' => $userId,
            'site_url' => $siteUrl, 'api_url' => $apiUrl, 'expires_at' => $expiresAt,
        ]);
    }

    public function consume(string $stateHash, int $workspaceId, int $userId): ?WordPressAuthRequest
    {
        return DB::transaction(function () use ($stateHash, $workspaceId, $userId): ?WordPressAuthRequest {
            $request = WordPressAuthRequest::query()->where('state_hash', $stateHash)
                ->where('workspace_id', $workspaceId)->where('user_id', $userId)
                ->where('expires_at', '>', CarbonImmutable::now())->lockForUpdate()->first();
            $request?->delete();

            return $request;
        });
    }
}
