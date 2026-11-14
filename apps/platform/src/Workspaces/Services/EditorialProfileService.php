<?php

namespace Modules\Workspaces\Services;

use Modules\Workspaces\Commands\SaveEditorialProfileCommand;
use Modules\Workspaces\Data\EditorialProfileData;
use Modules\Workspaces\Queries\EditorialProfileQuery;

final class EditorialProfileService
{
    public function __construct(
        private readonly EditorialProfileQuery $profile,
        private readonly SaveEditorialProfileCommand $save,
    ) {}

    public function show(int $workspaceId): EditorialProfileData
    {
        return EditorialProfileData::fromStored($this->profile->execute($workspaceId));
    }

    public function update(int $workspaceId, EditorialProfileData $data): EditorialProfileData
    {
        $clean = new EditorialProfileData(
            trim($data->audience), trim($data->voice), trim($data->topics_scope),
            array_values(array_unique(array_filter(array_map('trim', $data->banned_phrases)))), trim($data->example_post),
        );
        $this->save->execute($workspaceId, $clean->toArray());

        return $clean;
    }

    public function forPayload(int $workspaceId): ?array
    {
        $profile = $this->show($workspaceId);

        return array_filter($profile->toArray(), fn ($value) => $value !== '' && $value !== []) === [] ? null : $profile->toArray();
    }
}
