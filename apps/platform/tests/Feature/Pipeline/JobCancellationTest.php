<?php

namespace Tests\Feature\Pipeline;

use Modules\Pipeline\Enums\JobStatus;
use PHPUnit\Framework\Attributes\Test;
use Tests\Support\BuildsDomain;
use Tests\TestCase;

final class JobCancellationTest extends TestCase
{
    use BuildsDomain;

    protected function setUp(): void
    {
        parent::setUp();
        $this->signIn();
    }

    #[Test]
    public function cancelled_status_is_accepted_by_database(): void
    {
        $job = $this->makeJob();
        $job->forceFill(['status' => JobStatus::Cancelled])->save();

        $this->assertSame(JobStatus::Cancelled, $job->fresh()->status);
        $this->assertFalse(JobStatus::Cancelled->isActive());
    }
}
