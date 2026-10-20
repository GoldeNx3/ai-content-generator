<?php

namespace Modules\Workspaces\Services;

use Illuminate\Auth\AuthenticationException;
use Illuminate\Contracts\Auth\Factory as AuthFactory;
use Modules\Shared\Exceptions\ApiException;
use Modules\Workspaces\Data\WorkspaceData;
use Modules\Workspaces\Enums\WorkspaceRole;
use Modules\Workspaces\Queries\UserMembershipQuery;

final class CurrentWorkspace
{
    private ?WorkspaceData $resolved = null;

    public function __construct(
        private readonly AuthFactory $auth,
        private readonly UserMembershipQuery $membership,
    ) {}

    public function get(): WorkspaceData
    {
        if ($this->resolved !== null) {
            return $this->resolved;
        }
        $userId = $this->auth->guard()->id();
        if ($userId === null) {
            throw new AuthenticationException;
        }
        $preferred = session()->get('workspace_id');
        $workspace = ($preferred ? $this->membership->execute($userId, (int) $preferred) : null)
            ?? $this->membership->execute($userId);

        return $this->resolved = $workspace ?? throw new ApiException('no_workspace', 403);
    }

    public function id(): int
    {
        return $this->get()->id;
    }

    public function requireOwner(): void
    {
        if ($this->get()->role !== WorkspaceRole::Owner) {
            throw new ApiException('owner_required', 403);
        }
    }
}
