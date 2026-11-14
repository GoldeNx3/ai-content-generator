<?php

namespace Modules\Workspaces\Services;

use Illuminate\Auth\AuthenticationException;
use Illuminate\Contracts\Auth\Factory as AuthFactory;
use Modules\Shared\Exceptions\ApiException;
use Modules\Workspaces\Data\WorkspaceData;
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

        return $this->resolved = $this->membership->execute($userId) ?? throw new ApiException('no_workspace', 403);
    }

    public function id(): int
    {
        return $this->get()->id;
    }
}
