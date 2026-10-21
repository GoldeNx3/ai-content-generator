<?php

namespace Modules\WordPress\Services;

use Carbon\CarbonImmutable;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;
use Modules\Shared\Exceptions\ApiException;
use Modules\WordPress\Client\WordPressClientFactory;
use Modules\WordPress\Commands\AuthRequestCommand;
use Modules\WordPress\Commands\ConnectionCommand;
use Modules\WordPress\Data\ConnectionConfig;
use Modules\WordPress\Exceptions\WordPressException;
use Modules\WordPress\Models\WordPressConnection;
use Modules\WordPress\Queries\ConnectionForWorkspaceQuery;
use Modules\WordPress\Queries\LinkedPublicationsQuery;
use Modules\WordPress\Support\WordPressUrl;

final class ConnectionService
{
    private const APP_ID = '5b0b3f5e-6a8f-4f8e-9a51-6f1d3c2e7c10';

    private const APP_NAME = 'Content Engine';

    private const AUTH_TTL_MINUTES = 15;

    public function __construct(
        private readonly WordPressClientFactory $clients,
        private readonly ConnectionForWorkspaceQuery $connectionFor,
        private readonly LinkedPublicationsQuery $linked,
        private readonly ConnectionCommand $connections,
        private readonly AuthRequestCommand $authRequests,
    ) {}

    public function find(int $workspaceId): ?WordPressConnection
    {
        return $this->connectionFor->execute($workspaceId);
    }

    public function config(int $workspaceId): ConnectionConfig
    {
        $connection = $this->find($workspaceId) ?? throw new WordPressException('wordpress_not_configured');

        return ConnectionConfig::fromModel($connection);
    }

    public function connect(int $workspaceId, string $siteUrl, ?string $apiUrl, string $username, string $password, bool $confirmSiteChange): WordPressConnection
    {
        $siteUrl = WordPressUrl::normalize($siteUrl);
        $apiUrl = WordPressUrl::normalize($apiUrl, required: false);
        $username = trim($username);
        $password = trim($password);
        $existing = $this->find($workspaceId);
        $siteChanged = $existing !== null && $existing->site_url !== $siteUrl;
        if ($siteChanged && ! $confirmSiteChange && $this->linked->execute($workspaceId, $existing->instance_id)) {
            throw new ApiException('wordpress_site_change_requires_confirmation', 409);
        }
        try {
            $probe = $this->clients->make(new ConnectionConfig($siteUrl, $apiUrl, $username, $password))->testConnection();
        } catch (WordPressException $exception) {
            throw new ApiException($exception->errorCode, 422);
        }
        $caps = $probe['capabilities'];

        return DB::transaction(function () use ($existing, $workspaceId, $siteChanged, $siteUrl, $apiUrl, $username, $password, $probe, $caps): WordPressConnection {
            $instance = $existing?->instance_id ?? 'ce-'.Str::lower(Str::random(32));
            if ($siteChanged) {
                $this->connections->unlinkPublications($workspaceId, $existing->instance_id);
                $instance = 'ce-'.Str::lower(Str::random(32));
            }

            return $this->connections->save($existing, $workspaceId, [
                'site_url' => $siteUrl, 'api_url' => $apiUrl, 'username' => $username, 'app_password' => $password,
                'instance_id' => $instance, 'seo_plugin' => $this->seoPlugin($caps),
                'wp_user_id' => $probe['user_id'], 'wp_user_name' => $probe['user_name'],
                'can_publish' => (bool) ($caps['can_publish'] ?? false), 'last_checked_at' => CarbonImmutable::now(), 'last_error' => null,
            ]);
        });
    }

    public function test(int $workspaceId): WordPressConnection
    {
        $connection = $this->find($workspaceId) ?? throw new ApiException('wordpress_not_configured', 404);
        $attributes = ['last_checked_at' => CarbonImmutable::now(), 'last_error' => null];
        try {
            $caps = $this->clients->make(ConnectionConfig::fromModel($connection))->testConnection()['capabilities'];
            $attributes += ['can_publish' => (bool) ($caps['can_publish'] ?? false), 'seo_plugin' => $this->seoPlugin($caps)];
        } catch (WordPressException $exception) {
            $attributes['last_error'] = $exception->errorCode;
        }
        $connection->update($attributes);

        return $connection;
    }

    public function updateDefaults(int $workspaceId, array $values): WordPressConnection
    {
        $connection = $this->find($workspaceId) ?? throw new ApiException('wordpress_not_configured', 404);
        $connection->update($values);

        return $connection;
    }

    public function disconnect(int $workspaceId): void
    {
        $this->connections->delete($workspaceId);
    }

    public function startAuthorization(int $workspaceId, int $userId, string $siteUrl, ?string $apiUrl): string
    {
        $siteUrl = WordPressUrl::normalize($siteUrl);
        $apiUrl = WordPressUrl::normalize($apiUrl, required: false);
        try {
            $index = $this->clients->make(new ConnectionConfig($siteUrl, $apiUrl, '', ''))->index();
        } catch (WordPressException $exception) {
            throw new ApiException($exception->errorCode === 'wordpress_invalid_json' ? 'wordpress_not_wordpress' : $exception->errorCode, 422);
        }
        $endpoint = $index['authentication']['application-passwords']['endpoints']['authorization'] ?? null;
        if (! is_string($endpoint) || $endpoint === '') {
            throw new ApiException('wordpress_app_passwords_unavailable', 422);
        }
        $state = Str::random(48);
        $this->authRequests->create(hash('sha256', $state), $workspaceId, $userId, $siteUrl, $apiUrl, CarbonImmutable::now()->addMinutes(self::AUTH_TTL_MINUTES));
        $callback = rtrim(config('content.frontend_url'), '/').'/settings/wordpress/callback';

        return $endpoint.'?'.http_build_query([
            'app_name' => self::APP_NAME,
            'app_id' => self::APP_ID,
            'success_url' => $callback.'?'.http_build_query(['state' => $state]),
            'reject_url' => $callback.'?'.http_build_query(['state' => $state, 'rejected' => '1']),
        ]);
    }

    public function completeAuthorization(int $workspaceId, int $userId, string $state, string $username, string $password, bool $confirm): WordPressConnection
    {
        $request = $this->authRequests->consume(hash('sha256', $state), $workspaceId, $userId)
            ?? throw new ApiException('wordpress_auth_state_invalid', 400);

        return $this->connect($workspaceId, $request->site_url, $request->api_url, $username, $password, $confirm);
    }

    private function seoPlugin(array $caps): string
    {
        return in_array($caps['seo_plugin'] ?? null, ['yoast', 'rankmath', 'none'], true) ? $caps['seo_plugin'] : 'none';
    }
}
