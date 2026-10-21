<?php

namespace Modules\WordPress\Commands;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Modules\WordPress\Models\WordPressAuthRequest;

final class ConsumeAuthRequestCommand
{
    public function execute(string $stateHash, int $workspaceId, int $userId): ?WordPressAuthRequest
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
