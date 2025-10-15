/**
 * Configuration-Driven Data Collection Tests
 * 
 * Tests the selective sync functionality using different configuration profiles
 * and validates field-level filtering behavior.
 */

import { 
  SyncConfiguration,
  FULL_SYNC_PROFILE,
  STUDENTS_ONLY_PROFILE,
  ASSIGNMENTS_ONLY_PROFILE,
  LIGHTWEIGHT_PROFILE,
  ANALYTICS_PROFILE,
  getProfile,
  validateConfiguration,
  createCustomConfiguration,
  estimatePerformanceImpact,
  getPerformanceDescription
} from '../types/sync-configuration';

import { CanvasDataConstructor } from '../staging/canvas-data-constructor';
import { CanvasCourseApiDataSet } from '../staging/api-call-staging';
import { CanvasBulkApiDataManager } from '../staging/bulk-api-call-staging';

describe('Configuration System Tests', () => {
  
  describe('Configuration Schema Validation', () => {
    
    it('Should validate FULL_SYNC_PROFILE has all required properties', () => {
      expect(FULL_SYNC_PROFILE.courseInfo).toBe(true);
      expect(FULL_SYNC_PROFILE.students).toBe(true);
      expect(FULL_SYNC_PROFILE.assignments).toBe(true);
      expect(FULL_SYNC_PROFILE.modules).toBe(true);
      expect(FULL_SYNC_PROFILE.grades).toBe(true);
      
      expect(FULL_SYNC_PROFILE.studentFields.basicInfo).toBe(true);
      expect(FULL_SYNC_PROFILE.studentFields.scores).toBe(true);
      expect(FULL_SYNC_PROFILE.studentFields.analytics).toBe(true);
      expect(FULL_SYNC_PROFILE.studentFields.enrollmentDetails).toBe(true);
      
      expect(FULL_SYNC_PROFILE.assignmentFields.basicInfo).toBe(true);
      expect(FULL_SYNC_PROFILE.assignmentFields.timestamps).toBe(true);
      expect(FULL_SYNC_PROFILE.processing.enhanceWithTimestamps).toBe(true);
      expect(FULL_SYNC_PROFILE.processing.filterUngradedQuizzes).toBe(true);
    });
    
    it('Should validate STUDENTS_ONLY_PROFILE disables assignments', () => {
      expect(STUDENTS_ONLY_PROFILE.students).toBe(true);
      expect(STUDENTS_ONLY_PROFILE.assignments).toBe(false);
      expect(STUDENTS_ONLY_PROFILE.modules).toBe(false);
      expect(STUDENTS_ONLY_PROFILE.processing.enhanceWithTimestamps).toBe(false);
    });
    
    it('Should validate ASSIGNMENTS_ONLY_PROFILE disables students', () => {
      expect(ASSIGNMENTS_ONLY_PROFILE.assignments).toBe(true);
      expect(ASSIGNMENTS_ONLY_PROFILE.modules).toBe(true);
      expect(ASSIGNMENTS_ONLY_PROFILE.students).toBe(false);
      expect(ASSIGNMENTS_ONLY_PROFILE.grades).toBe(false);
    });
    
    it('Should validate LIGHTWEIGHT_PROFILE has minimal settings', () => {
      expect(LIGHTWEIGHT_PROFILE.students).toBe(true);
      expect(LIGHTWEIGHT_PROFILE.assignments).toBe(true);
      expect(LIGHTWEIGHT_PROFILE.modules).toBe(false); // Lightweight
      expect(LIGHTWEIGHT_PROFILE.studentFields.analytics).toBe(false); // Minimal
      expect(LIGHTWEIGHT_PROFILE.assignmentFields.timestamps).toBe(false); // Minimal
      expect(LIGHTWEIGHT_PROFILE.processing.enhanceWithTimestamps).toBe(false); // Fast
    });
    
  });
  
  describe('Configuration Utilities', () => {
    
    it('Should retrieve profiles by name', () => {
      const fullProfile = getProfile('FULL');
      expect(fullProfile).toEqual(FULL_SYNC_PROFILE);
      
      const studentsProfile = getProfile('STUDENTS_ONLY');
      expect(studentsProfile).toEqual(STUDENTS_ONLY_PROFILE);
    });
    
    it('Should validate partial configurations', () => {
      const partialConfig: Partial<SyncConfiguration> = {
        students: false,
        assignments: true
      };
      
      const validated = validateConfiguration(partialConfig);
      
      // Should merge with FULL profile defaults
      expect(validated.students).toBe(false); // From partial
      expect(validated.assignments).toBe(true); // From partial
      expect(validated.courseInfo).toBe(true); // From FULL default
      expect(validated.studentFields.basicInfo).toBe(true); // From FULL default
    });
    
    it('Should create custom configurations', () => {
      const custom = createCustomConfiguration('LIGHTWEIGHT', {
        processing: {
          enhanceWithTimestamps: true,
          filterUngradedQuizzes: true,
          resolveQuizAssignments: true,
          includeUnpublished: false
        }
      });
      
      // Should have LIGHTWEIGHT base with custom processing
      expect(custom.modules).toBe(false); // From LIGHTWEIGHT
      expect(custom.processing.enhanceWithTimestamps).toBe(true); // From override
    });
    
  });
  
  describe('Performance Estimation', () => {
    
    it('Should estimate performance impact correctly', () => {
      const fullImpact = estimatePerformanceImpact(FULL_SYNC_PROFILE);
      const lightweightImpact = estimatePerformanceImpact(LIGHTWEIGHT_PROFILE);
      const studentsOnlyImpact = estimatePerformanceImpact(STUDENTS_ONLY_PROFILE);
      
      expect(fullImpact).toBeGreaterThanOrEqual(0.9); // Full sync = near max impact
      expect(lightweightImpact).toBeLessThan(fullImpact);
      expect(studentsOnlyImpact).toBeLessThan(lightweightImpact);
    });
    
    it('Should provide correct performance descriptions', () => {
      expect(getPerformanceDescription(FULL_SYNC_PROFILE)).toBe('Full Sync');
      expect(getPerformanceDescription(LIGHTWEIGHT_PROFILE)).toMatch(/(Very Fast|Fast|Moderate)/);
      expect(getPerformanceDescription(STUDENTS_ONLY_PROFILE)).toMatch(/(Very Fast|Fast)/);
    });
    
  });
  
});

describe('Configuration-Driven Data Collection', () => {
  
  // Mock Canvas API for consistent testing
  const mockCanvasApi = {
    getCourse: jest.fn(),
    getCourseStudents: jest.fn(),
    getCourseAssignments: jest.fn(),
    getCourseModules: jest.fn(),
    getCourseEnrollments: jest.fn(),
  };
  
  beforeEach(() => {
    // Reset mocks
    jest.clearAllMocks();
    
    // Setup default mock responses
    mockCanvasApi.getCourse.mockResolvedValue({
      id: 12345,
      name: 'Test Course',
      course_code: 'TEST-101'
    });
    
    mockCanvasApi.getCourseEnrollments.mockResolvedValue([
      {
        student_id: 2001,
        user_id: 2001,
        name: 'Test Student',
        current_score: 85,
        final_score: 90
      }
    ]);
    
    mockCanvasApi.getCourseModules.mockResolvedValue([
      {
        id: 3001,
        name: 'Test Module',
        assignments: [
          {
            id: 9001,
            name: 'Test Assignment',
            points_possible: 10
          }
        ]
      }
    ]);
  });
  
  describe('CanvasDataConstructor Configuration Tests', () => {
    
    it('Should use FULL_SYNC_PROFILE by default', () => {
      const constructor = new CanvasDataConstructor({ canvasApi: mockCanvasApi });
      expect((constructor as any).config).toEqual(FULL_SYNC_PROFILE);
    });
    
    it('Should accept custom configuration', () => {
      const customConfig = STUDENTS_ONLY_PROFILE;
      const constructor = new CanvasDataConstructor({ 
        canvasApi: mockCanvasApi, 
        config: customConfig 
      });
      
      expect((constructor as any).config).toEqual(STUDENTS_ONLY_PROFILE);
    });
    
  });
  
  describe('CanvasCourseApiDataSet Configuration Tests', () => {
    
    it('Should use FULL_SYNC_PROFILE by default', () => {
      const dataSet = new CanvasCourseApiDataSet(12345);
      expect(dataSet.config).toEqual(FULL_SYNC_PROFILE);
    });
    
    it('Should accept custom configuration', () => {
      const dataSet = new CanvasCourseApiDataSet(12345, LIGHTWEIGHT_PROFILE);
      expect(dataSet.config).toEqual(LIGHTWEIGHT_PROFILE);
    });
    
    it('Should skip student rebuild when students disabled', async () => {
      const dataSet = new CanvasCourseApiDataSet(12345, ASSIGNMENTS_ONLY_PROFILE);
      const mockConstructor = {
        getStudentsData: jest.fn().mockResolvedValue([])
      };
      
      console.log = jest.fn(); // Mock console.log
      
      await dataSet.rebuildEnrollments(mockConstructor);
      
      // Should skip and log
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining('Skipping enrollment rebuild')
      );
      expect(mockConstructor.getStudentsData).not.toHaveBeenCalled();
    });
    
    it('Should skip assignment rebuild when assignments disabled', async () => {
      const dataSet = new CanvasCourseApiDataSet(12345, STUDENTS_ONLY_PROFILE);
      const mockConstructor = {
        getModulesData: jest.fn().mockResolvedValue([])
      };
      
      console.log = jest.fn(); // Mock console.log
      
      await dataSet.rebuildAssignments(mockConstructor);
      
      // Should skip and log
      expect(console.log).toHaveBeenCalledWith(
        expect.stringContaining('Skipping assignment rebuild')
      );
      expect(mockConstructor.getModulesData).not.toHaveBeenCalled();
    });
    
  });
  
  describe('CanvasBulkApiDataManager Configuration Tests', () => {
    
    it('Should use FULL_SYNC_PROFILE by default', () => {
      const bulkManager = new CanvasBulkApiDataManager();
      expect(bulkManager.config).toEqual(FULL_SYNC_PROFILE);
    });
    
    it('Should accept and propagate custom configuration', () => {
      const bulkManager = new CanvasBulkApiDataManager(ANALYTICS_PROFILE);
      expect(bulkManager.config).toEqual(ANALYTICS_PROFILE);
      
      // Initialize a course data set and check it gets the config
      bulkManager.initializeCourseDataSets([12345]);
      const courseDataSet = bulkManager.getCourseDataSet(12345);
      expect(courseDataSet.config).toEqual(ANALYTICS_PROFILE);
    });
    
  });
  
  describe('Configuration Impact on Data Collection', () => {
    
    it('Should collect different data based on configuration', () => {
      // This would be tested with integration tests using real Canvas API
      // Here we verify that the configurations are set up correctly
      
      const fullConfig = FULL_SYNC_PROFILE;
      const lightweightConfig = LIGHTWEIGHT_PROFILE;
      
      // Full config enables everything
      expect(fullConfig.students && fullConfig.assignments && fullConfig.modules).toBe(true);
      expect(fullConfig.processing.enhanceWithTimestamps).toBe(true);
      
      // Lightweight disables heavy processing
      expect(lightweightConfig.modules).toBe(false);
      expect(lightweightConfig.processing.enhanceWithTimestamps).toBe(false);
      expect(lightweightConfig.studentFields.analytics).toBe(false);
      expect(lightweightConfig.assignmentFields.timestamps).toBe(false);
    });
    
  });
  
});

describe('Configuration Profile Performance Characteristics', () => {
  
  it('Should have expected performance rankings', () => {
    const profiles = [
      { name: 'FULL', config: FULL_SYNC_PROFILE },
      { name: 'ANALYTICS', config: ANALYTICS_PROFILE },
      { name: 'ASSIGNMENTS_ONLY', config: ASSIGNMENTS_ONLY_PROFILE },
      { name: 'LIGHTWEIGHT', config: LIGHTWEIGHT_PROFILE },
      { name: 'STUDENTS_ONLY', config: STUDENTS_ONLY_PROFILE }
    ];
    
    const impacts = profiles.map(p => ({
      name: p.name,
      impact: estimatePerformanceImpact(p.config),
      description: getPerformanceDescription(p.config)
    }));
    
    console.log('\n📊 Configuration Performance Rankings:');
    impacts
      .sort((a, b) => b.impact - a.impact)
      .forEach((profile, index) => {
        console.log(`   ${index + 1}. ${profile.name}: ${profile.impact.toFixed(2)} (${profile.description})`);
      });
    
    // Validate expected ordering (FULL should be highest impact)
    const fullImpact = impacts.find(p => p.name === 'FULL')?.impact || 0;
    const studentsOnlyImpact = impacts.find(p => p.name === 'STUDENTS_ONLY')?.impact || 0;
    
    expect(fullImpact).toBeGreaterThan(studentsOnlyImpact);
  });
  
});